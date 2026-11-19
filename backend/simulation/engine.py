"""Live field simulator.

Soil moisture moves on an accelerated clock. Valve safety uses wall-clock time.
Restarting the process closes every valve. Moisture continues from the last
saved raw reading so a reboot does not jump the field back to the starting story.
Delete data/kshetra.db when you want the original starting values.
"""

from __future__ import annotations

import logging
import random
import threading
from collections import deque
from dataclasses import dataclass
from datetime import timedelta

from backend.database.db import Database
from backend.irrigation.safety import SafetyError, open_is_allowed, valve_should_force_close
from backend.irrigation.sprinklers import sprinkler_action
from backend.sensors.health import judge_zone
from backend.simulation.moisture import advance_moisture, apply_calibration
from backend.utils.timeutil import as_utc, utc_iso, utc_now

LOGGER = logging.getLogger("kshetra.sim")


def _rover_label(status: str, checkpoint: str | None) -> str:
    if status == "inspecting" and checkpoint:
        return f"Stopped at {checkpoint} for a photo."
    if status == "inspecting":
        return "Stopped for a photo."
    if status == "moving":
        return "Patrolling the field lane."
    return "At the dock."


@dataclass
class SimSensor:
    id: str
    zone_id: str
    label: str
    x: float
    y: float
    moisture: float
    dry_rate_per_hour: float
    irrigate_rate_per_hour: float
    noise: float
    calibration_offset: float
    calibration_scale: float
    failed: bool = False


@dataclass
class SimZone:
    id: str
    name: str
    crop_label: str
    low_threshold: float
    target_moisture: float
    max_duration_sec: int
    cooldown_sec: int
    bounds: dict
    valve_open: bool = False
    opened_wall: object | None = None
    last_closed_wall: object | None = None
    last_stop_reason: str | None = None


class FieldSimulator:
    """Device adapter used while the laboratory hardware is unavailable."""

    allows_fault_injection = True

    def __init__(self, db: Database, field: dict, tick_wall_seconds: float = 1.0):
        self.db = db
        self.field = field
        self.time_scale = float(field["time_scale"])
        self.persist_every = float(field["persist_every_wall_seconds"])
        self.tick_wall_seconds = tick_wall_seconds
        self.rules = field["safety"]
        self.rng = random.Random(int(field["seed"]))
        self.started_wall = utc_now()
        self.sim_elapsed = 0.0
        self.emergency = False
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_persist = None
        self._previous_quality: dict[str, str] = {}
        self._previous_zone: dict[str, str] = {}
        self.tick_hooks = []
        self.rover_progress = 0.0
        self.rover_direction = 1
        self.rover_pause = 0.0
        self.rover_status = "parked"
        self.rover_checkpoint = None
        self._rover_paused_at: set[str] = set()

        latest = db.latest_raw()
        self.zones: dict[str, SimZone] = {}
        for spec in field["zones"]:
            self.zones[spec["id"]] = SimZone(
                id=spec["id"],
                name=spec["name"],
                crop_label=spec["crop_label"],
                low_threshold=float(spec["low_threshold"]),
                target_moisture=float(spec["target_moisture"]),
                max_duration_sec=int(spec["max_duration_sec"]),
                cooldown_sec=int(spec["cooldown_sec"]),
                bounds=spec["bounds"],
            )
        self.sensors: list[SimSensor] = []
        self._sensor_map: dict[str, SimSensor] = {}
        for spec in field["sensors"]:
            sensor = SimSensor(
                id=spec["id"],
                zone_id=spec["zone_id"],
                label=spec["label"],
                x=float(spec["x"]),
                y=float(spec["y"]),
                moisture=float(latest.get(spec["id"], spec["initial_moisture"])),
                dry_rate_per_hour=float(spec["dry_rate_per_hour"]),
                irrigate_rate_per_hour=float(spec["irrigate_rate_per_hour"]),
                noise=float(spec["noise"]),
                calibration_offset=float(spec["calibration_offset"]),
                calibration_scale=float(spec["calibration_scale"]),
            )
            self.sensors.append(sensor)
            self._sensor_map[sensor.id] = sensor
        self.history = {zone_id: deque(maxlen=180) for zone_id in self.zones}
        self._zone_judgements = {}
        self._judgements = {}
        self._recompute(self.started_wall, persist=True, record_history=True)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="kshetra-sim", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def step(self, dt_sim_seconds: float | None = None, now=None, persist: bool | None = None) -> dict:
        with self._lock:
            moment = as_utc(now) if now is not None else utc_now()
            if dt_sim_seconds is None:
                dt_sim_seconds = self.time_scale * self.tick_wall_seconds
            if dt_sim_seconds < 0:
                raise ValueError("Simulated timestep cannot be negative.")
            self.sim_elapsed += dt_sim_seconds
            for zone in self.zones.values():
                if zone.valve_open and zone.opened_wall is not None:
                    elapsed = (moment - zone.opened_wall).total_seconds()
                    force, why = valve_should_force_close(elapsed, zone.max_duration_sec, self.emergency)
                    if force and why is not None:
                        self._close_zone(zone, why, moment)
            dt_hours = dt_sim_seconds / 3600.0
            for sensor in self.sensors:
                sensor.moisture = advance_moisture(
                    sensor.moisture,
                    valve_open=self.zones[sensor.zone_id].valve_open,
                    dt_hours=dt_hours,
                    dry_rate=sensor.dry_rate_per_hour,
                    irrigate_rate=sensor.irrigate_rate_per_hour,
                    noise=sensor.noise,
                    rng=self.rng,
                )
            do_persist = self._persist_due(moment) if persist is None else persist
            self._recompute(moment, persist=do_persist, record_history=True)
            self._apply_sprinklers(moment)
            wall_dt = dt_sim_seconds / self.time_scale if self.time_scale else dt_sim_seconds
            self._move_rover(wall_dt)
            snapshot = self._snapshot_unlocked(moment)
        for hook in list(self.tick_hooks):
            hook(moment, self.emergency)
        return snapshot

    def snapshot(self) -> dict:
        with self._lock:
            return self._snapshot_unlocked(utc_now())

    def set_valve(self, zone_id: str, open_valve: bool, reason: str) -> dict:
        with self._lock:
            zone = self.zones.get(zone_id)
            if zone is None:
                raise KeyError(zone_id)
            moment = utc_now()
            if open_valve:
                allowed, message = open_is_allowed(self.emergency)
                if not allowed:
                    raise SafetyError(message)
                if not zone.valve_open:
                    zone.valve_open = True
                    zone.opened_wall = moment
                    zone.last_stop_reason = None
                    self.db.open_irrigation(zone_id, "manual", reason, utc_iso(moment), "simulated")
            elif zone.valve_open:
                self._close_zone(zone, "manual", moment)
            return self._snapshot_unlocked(moment)

    def emergency_stop(self) -> dict:
        with self._lock:
            self.emergency = True
            moment = utc_now()
            for zone in self.zones.values():
                if zone.valve_open:
                    self._close_zone(zone, "emergency_stop", moment)
            return self._snapshot_unlocked(moment)

    def reset_emergency(self) -> dict:
        with self._lock:
            self.emergency = False
            return self._snapshot_unlocked(utc_now())

    def set_sensor_failed(self, sensor_id: str, failed: bool) -> None:
        with self._lock:
            sensor = self._sensor_map.get(sensor_id)
            if sensor is None:
                raise KeyError(sensor_id)
            sensor.failed = bool(failed)
            self._recompute(utc_now(), persist=True, record_history=True)

    def _loop(self) -> None:
        while not self._stop.wait(self.tick_wall_seconds):
            try:
                self.step()
            except Exception:
                LOGGER.exception("Simulator tick failed")

    def _close_zone(self, zone: SimZone, stop_reason: str, moment) -> None:
        if not zone.valve_open:
            return
        opened = zone.opened_wall or moment
        duration = round(max(0.0, (moment - opened).total_seconds()), 1)
        zone.valve_open = False
        zone.opened_wall = None
        zone.last_closed_wall = moment
        zone.last_stop_reason = stop_reason
        self.db.close_irrigation(zone.id, utc_iso(moment), stop_reason, duration)

    def _open_zone(self, zone: SimZone, mode: str, reason: str, moment) -> None:
        if zone.valve_open:
            return
        allowed, _message = open_is_allowed(self.emergency)
        if not allowed:
            return
        zone.valve_open = True
        zone.opened_wall = moment
        zone.last_stop_reason = None
        self.db.open_irrigation(zone.id, mode, reason, utc_iso(moment), "simulated")

    def _apply_sprinklers(self, moment) -> None:
        for zone in self.zones.values():
            judgement = self._zone_judgements[zone.id]
            since = None
            if zone.last_closed_wall is not None:
                since = (moment - zone.last_closed_wall).total_seconds()
            action = sprinkler_action(
                status=judgement.status,
                average=judgement.average,
                low=zone.low_threshold,
                target=zone.target_moisture,
                valve_open=zone.valve_open,
                seconds_since_close=since,
                cooldown_sec=zone.cooldown_sec,
                emergency=self.emergency,
            )
            if action == "open":
                self._open_zone(zone, "automatic", "dry_soil", moment)
            elif action == "close_target":
                self._close_zone(zone, "target_reached", moment)
            elif action == "close_unsafe":
                self._close_zone(zone, "sensors_not_agreed", moment)

    def _move_rover(self, wall_dt: float) -> None:
        if wall_dt <= 0 or not self.field["routes"]:
            return
        if self.rover_pause > 0:
            self.rover_pause = max(0.0, self.rover_pause - wall_dt)
            self.rover_status = "inspecting"
            return
        route = self.field["routes"][0]
        self.rover_status = "moving"
        self.rover_progress += self.rover_direction * 0.04 * wall_dt
        if self.rover_progress >= 1:
            self.rover_progress = 1
            self.rover_direction = -1
            self._rover_paused_at.clear()
        elif self.rover_progress <= 0:
            self.rover_progress = 0
            self.rover_direction = 1
            self._rover_paused_at.clear()
            self.rover_status = "parked"
        start = route["points"][0]
        end = route["points"][-1]
        y = start[1] + (end[1] - start[1]) * self.rover_progress
        nearest = None
        nearest_gap = 2.0
        for checkpoint in route["checkpoints"]:
            gap = abs(checkpoint["y"] - y)
            if gap < nearest_gap:
                nearest = checkpoint["id"]
                nearest_gap = gap
        if nearest and nearest not in self._rover_paused_at and self.rover_status == "moving":
            self._rover_paused_at.add(nearest)
            self.rover_checkpoint = nearest
            self.rover_pause = 4
            self.rover_status = "inspecting"

    def _persist_due(self, moment) -> bool:
        if self._last_persist is None:
            return True
        return (moment - self._last_persist).total_seconds() >= self.persist_every

    def _sim_clock(self):
        return self.started_wall + timedelta(seconds=self.sim_elapsed)

    def _recompute(self, moment, persist: bool, record_history: bool) -> None:
        grouped = {zone_id: [] for zone_id in self.zones}
        for sensor in self.sensors:
            raw = None if sensor.failed else sensor.moisture
            value = apply_calibration(raw, sensor.calibration_scale, sensor.calibration_offset)
            grouped[sensor.zone_id].append((sensor.id, value))

        self._zone_judgements = {}
        self._judgements = {}
        for zone_id, samples in grouped.items():
            judgement = judge_zone(
                samples,
                min_sensors=int(self.rules["min_sensors_for_decision"]),
                suspect_gap=float(self.rules["suspect_gap_points"]),
                neighbor_agreement=float(self.rules["neighbor_agreement_points"]),
                uneven_spread=float(self.rules["uneven_spread_points"]),
            )
            self._zone_judgements[zone_id] = judgement
            for item in judgement.sensors:
                self._judgements[item.sensor_id] = item

        if record_history:
            stamp = utc_iso(self._sim_clock())
            for zone_id, judgement in self._zone_judgements.items():
                self.history[zone_id].append({"t": stamp, "average": judgement.average})

        self._sync_alerts(utc_iso(moment))
        if persist:
            self.db.insert_readings(self._reading_rows(moment))
            self._last_persist = moment

    def _sync_alerts(self, now_iso: str) -> None:
        for sensor in self.sensors:
            judgement = self._judgements[sensor.id]
            previous = self._previous_quality.get(sensor.id)
            if judgement.quality == "ok":
                if previous not in (None, "ok"):
                    for kind in ("suspect", "missing", "invalid"):
                        self.db.acknowledge_code(f"{sensor.id}:{kind}", now_iso)
            elif previous != judgement.quality:
                severity = "warning" if judgement.quality == "suspect" else "danger"
                self.db.raise_alert(
                    severity,
                    f"{sensor.id}:{judgement.quality}",
                    f"{sensor.label} sensor in {self.zones[sensor.zone_id].name}: {judgement.reason}",
                    sensor.id,
                )
            self._previous_quality[sensor.id] = judgement.quality

        for zone_id, judgement in self._zone_judgements.items():
            zone = self.zones[zone_id]
            insufficient = f"{zone_id}:insufficient"
            uneven = f"{zone_id}:uneven"
            previous = self._previous_zone.get(zone_id)
            if judgement.status == "insufficient":
                if previous != "insufficient":
                    self.db.raise_alert("danger", insufficient, f"{zone.name}: {judgement.summary}", zone_id)
                self.db.acknowledge_code(uneven, now_iso)
            elif judgement.status == "uneven":
                if previous != "uneven":
                    self.db.raise_alert("warning", uneven, f"{zone.name}: {judgement.summary}", zone_id)
                self.db.acknowledge_code(insufficient, now_iso)
            elif previous not in (None, "ok"):
                self.db.acknowledge_code(insufficient, now_iso)
                self.db.acknowledge_code(uneven, now_iso)
            self._previous_zone[zone_id] = judgement.status

    def _reading_rows(self, moment) -> list[dict]:
        wall = utc_iso(moment)
        sim_time = utc_iso(self._sim_clock())
        rows = []
        for sensor in self.sensors:
            judgement = self._judgements[sensor.id]
            raw = None if sensor.failed else round(sensor.moisture, 2)
            moisture = None if judgement.moisture is None else round(judgement.moisture, 2)
            if judgement.quality == "missing":
                raw = None
                moisture = None
            rows.append(
                {
                    "sensor_id": sensor.id,
                    "raw_percent": raw,
                    "moisture_percent": moisture,
                    "quality": judgement.quality,
                    "source": "simulated",
                    "recorded_at": wall,
                    "sim_time": sim_time,
                }
            )
        return rows

    def _snapshot_unlocked(self, moment) -> dict:
        zones = []
        sensors = []
        for zone in self.zones.values():
            judgement = self._zone_judgements[zone.id]
            if zone.valve_open and zone.opened_wall is not None:
                seconds_open = max(0, int((moment - zone.opened_wall).total_seconds()))
            else:
                seconds_open = 0
            zones.append(
                {
                    "id": zone.id,
                    "name": zone.name,
                    "crop_label": zone.crop_label,
                    "low_threshold": zone.low_threshold,
                    "target_moisture": zone.target_moisture,
                    "max_duration_sec": zone.max_duration_sec,
                    "bounds": zone.bounds,
                    "valve_open": zone.valve_open,
                    "seconds_open": seconds_open,
                    "last_stop_reason": zone.last_stop_reason,
                    "average": judgement.average,
                    "included_count": judgement.included_count,
                    "status": judgement.status,
                    "summary": judgement.summary,
                    "moisture_source": "simulated",
                    "history": list(self.history[zone.id]),
                }
            )
        for sensor in self.sensors:
            judgement = self._judgements[sensor.id]
            sensors.append(
                {
                    "id": sensor.id,
                    "zone_id": sensor.zone_id,
                    "label": sensor.label,
                    "x": sensor.x,
                    "y": sensor.y,
                    "moisture": None if judgement.moisture is None else round(judgement.moisture, 1),
                    "quality": judgement.quality,
                    "reason": judgement.reason,
                    "failed": sensor.failed,
                    "source": "simulated",
                }
            )
        rovers = []
        for route in self.field["routes"]:
            start = route["points"][0]
            end = route["points"][-1]
            progress = self.rover_progress
            rovers.append(
                {
                    "id": route["rover_id"],
                    "name": route["name"],
                    "role": "doctor",
                    "status": self.rover_status,
                    "status_label": _rover_label(self.rover_status, self.rover_checkpoint),
                    "x": start[0] + (end[0] - start[0]) * progress,
                    "y": start[1] + (end[1] - start[1]) * progress,
                    "route_id": route["id"],
                    "checkpoint_id": self.rover_checkpoint,
                    "note": "One doctor rover patrols this lane, photographs plants, and sends the pictures to the Pi.",
                }
            )
        return {
            "source": "simulated",
            "hardware_connected": False,
            "phase": 2,
            "disclaimer": "Simulated moisture. No field sensor is connected, and these numbers are not calibrated measurements.",
            "model_note": "Drying and wetting speeds are demo settings, not a soil-physics model.",
            "water_note": "Water use is not shown. This build does not invent a litre measurement.",
            "automation_note": "A sprinkler turns on when its zone is dry and two sensors agree. It stops at the target, at the time limit, or on emergency stop.",
            "wall_time": utc_iso(moment),
            "sim_time": utc_iso(self._sim_clock()),
            "time_scale": self.time_scale,
            "emergency_stop": self.emergency,
            "map": self.field.get("map", {"width": 100, "height": 100, "north": "top"}),
            "zones": zones,
            "sensors": sensors,
            "pipes": self.field["pipes"],
            "road": self.field["road"],
            "routes": self.field["routes"],
            "rovers": rovers,
            "alerts": self.db.recent_alerts(),
        }
