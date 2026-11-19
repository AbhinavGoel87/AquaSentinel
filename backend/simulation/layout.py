"""Load and check the exhibition field file."""

from __future__ import annotations

import json
import math
from pathlib import Path


class FieldConfigError(ValueError):
    """data/field.json is missing or inconsistent."""


def load_field(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FieldConfigError(f"Field file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FieldConfigError(f"Field file is not valid JSON: {exc}") from exc
    validate_field(data)
    return data


def validate_field(data: dict) -> None:
    if not isinstance(data, dict):
        raise FieldConfigError("Field file must contain a JSON object.")

    time_scale = _number(data.get("time_scale"), "time_scale")
    if not 0 < time_scale <= 3600:
        raise FieldConfigError("time_scale must be greater than 0 and at most 3600.")
    persist = _number(data.get("persist_every_wall_seconds"), "persist_every_wall_seconds")
    if persist <= 0:
        raise FieldConfigError("persist_every_wall_seconds must be greater than 0.")
    seed = data.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise FieldConfigError("seed must be an integer.")

    safety = data.get("safety")
    if not isinstance(safety, dict):
        raise FieldConfigError("safety settings are missing.")
    for key in (
        "min_sensors_for_decision",
        "suspect_gap_points",
        "neighbor_agreement_points",
        "uneven_spread_points",
    ):
        if key not in safety:
            raise FieldConfigError(f"safety.{key} is missing.")
    min_sensors = safety["min_sensors_for_decision"]
    if isinstance(min_sensors, bool) or not isinstance(min_sensors, int) or min_sensors < 2:
        raise FieldConfigError("A zone decision needs at least 2 sensors.")

    zones = data.get("zones")
    sensors = data.get("sensors")
    if not isinstance(zones, list) or len(zones) != 2:
        raise FieldConfigError("Kshetra requires exactly 2 irrigation zones.")
    if not isinstance(sensors, list) or len(sensors) != 6:
        raise FieldConfigError("Kshetra requires exactly 6 soil sensors.")

    zone_ids = []
    for zone in zones:
        zone_id = _token(zone.get("id"), "zone id")
        zone_ids.append(zone_id)
        _text(zone.get("name"), f"{zone_id} name")
        _text(zone.get("crop_label"), f"{zone_id} crop_label")
        low = _number(zone.get("low_threshold"), f"{zone_id} low_threshold")
        target = _number(zone.get("target_moisture"), f"{zone_id} target_moisture")
        if not 0 <= low < target <= 100:
            raise FieldConfigError(f"{zone_id} needs 0 <= low_threshold < target_moisture <= 100.")
        limit = zone.get("max_duration_sec")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 3600:
            raise FieldConfigError(f"{zone_id} max_duration_sec must be 1 to 3600 seconds.")
        cooldown = zone.get("cooldown_sec")
        if isinstance(cooldown, bool) or not isinstance(cooldown, int) or cooldown < 0:
            raise FieldConfigError(f"{zone_id} cooldown_sec must be a non-negative integer.")
        _bounds(zone.get("bounds"), zone_id)
    if len(set(zone_ids)) != 2:
        raise FieldConfigError("Zone ids must be unique.")

    sensor_ids = []
    counts = {zone_id: 0 for zone_id in zone_ids}
    for sensor in sensors:
        sensor_id = _token(sensor.get("id"), "sensor id")
        sensor_ids.append(sensor_id)
        zone_id = sensor.get("zone_id")
        if zone_id not in counts:
            raise FieldConfigError(f"{sensor_id} belongs to an unknown zone.")
        counts[zone_id] += 1
        _text(sensor.get("label"), f"{sensor_id} label")
        _number(sensor.get("x"), f"{sensor_id} x")
        _number(sensor.get("y"), f"{sensor_id} y")
        initial = _number(sensor.get("initial_moisture"), f"{sensor_id} initial_moisture")
        if not 0 <= initial <= 100:
            raise FieldConfigError(f"{sensor_id} initial_moisture must be between 0 and 100.")
        dry = _number(sensor.get("dry_rate_per_hour"), f"{sensor_id} dry_rate_per_hour")
        wet = _number(sensor.get("irrigate_rate_per_hour"), f"{sensor_id} irrigate_rate_per_hour")
        noise = _number(sensor.get("noise"), f"{sensor_id} noise")
        if dry < 0 or wet < 0 or noise < 0:
            raise FieldConfigError(f"{sensor_id} rates and noise must be zero or positive.")
        _number(sensor.get("calibration_offset"), f"{sensor_id} calibration_offset")
        _number(sensor.get("calibration_scale"), f"{sensor_id} calibration_scale")
    if len(set(sensor_ids)) != 6:
        raise FieldConfigError("Sensor ids must be unique.")
    for zone_id, count in counts.items():
        if count != 3:
            raise FieldConfigError(f"{zone_id} must have 3 sensors, found {count}.")

    road = data.get("road")
    _bounds(road, "road")
    ordered = sorted(zones, key=lambda zone: zone["bounds"]["x"])
    left = ordered[0]["bounds"]
    right = ordered[1]["bounds"]
    if left["x"] + left["w"] > road["x"] or road["x"] + road["w"] > right["x"]:
        raise FieldConfigError("The road and dock must sit between the two zones.")

    pipes = data.get("pipes")
    if not isinstance(pipes, list) or not pipes:
        raise FieldConfigError("The field needs irrigation pipe segments.")
    for index, pipe in enumerate(pipes):
        for key in ("x1", "y1", "x2", "y2"):
            _number(pipe.get(key), f"pipes[{index}].{key}")

    routes = data.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise FieldConfigError("One doctor rover route is required.")
    rover_ids = []
    checkpoint_ids = []
    for route in routes:
        rover_id = _token(route.get("rover_id"), "rover id")
        rover_ids.append(rover_id)
        _token(route.get("id"), f"{rover_id} route id")
        _text(route.get("name"), f"{rover_id} name")
        points = route.get("points")
        if not isinstance(points, list) or len(points) < 2:
            raise FieldConfigError(f"{rover_id} needs a route with at least two points.")
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise FieldConfigError(f"{rover_id} route points must be [x, y] pairs.")
            _number(point[0], "x")
            _number(point[1], "y")
        checkpoints = route.get("checkpoints")
        if not isinstance(checkpoints, list) or len(checkpoints) < 1:
            raise FieldConfigError(f"{rover_id} needs inspection checkpoints.")
        for checkpoint in checkpoints:
            checkpoint_id = _token(checkpoint.get("id"), "checkpoint id")
            checkpoint_ids.append(checkpoint_id)
            _text(checkpoint.get("name"), f"{checkpoint_id} name")
            _number(checkpoint.get("x"), f"{checkpoint_id} x")
            _number(checkpoint.get("y"), f"{checkpoint_id} y")
        dock = route.get("dock")
        if not isinstance(dock, dict):
            raise FieldConfigError(f"{rover_id} needs a dock.")
        dock_x = _number(dock.get("x"), "dock x")
        _number(dock.get("y"), "dock y")
        if not road["x"] <= dock_x <= road["x"] + road["w"]:
            raise FieldConfigError(f"{rover_id} dock must be on the center road.")

    if rover_ids != ["rover1"]:
        raise FieldConfigError("The doctor rover id must be rover1.")
    if len(set(checkpoint_ids)) != len(checkpoint_ids):
        raise FieldConfigError("Checkpoint ids must be unique.")


def _number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FieldConfigError(f"{label} must be a number.")
    if not math.isfinite(value):
        raise FieldConfigError(f"{label} must be a finite number.")
    return float(value)


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FieldConfigError(f"{label} must be a non-empty string.")
    return value


def _token(value, label: str) -> str:
    text = _text(value, label)
    if any(character in text for character in ("/", " ", "#")):
        raise FieldConfigError(f"{label} must be a simple id without spaces or slashes.")
    return text


def _bounds(value, zone_id: str) -> None:
    if not isinstance(value, dict):
        raise FieldConfigError(f"{zone_id} bounds are missing.")
    for key in ("x", "y", "w", "h"):
        number = _number(value.get(key), f"{zone_id} bounds.{key}")
        if key in ("w", "h") and number <= 0:
            raise FieldConfigError(f"{zone_id} bounds.{key} must be greater than 0.")
