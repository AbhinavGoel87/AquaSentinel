"""Simulator behaviour with noise removed so the numbers are exact."""

import random
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from backend.database.db import Database
from backend.irrigation.safety import SafetyError
from backend.simulation.engine import FieldSimulator
from backend.simulation.layout import load_field
from backend.simulation.moisture import advance_moisture
from tests.support import ROOT


def build(directory: Path):
    field = load_field(ROOT / "data" / "field.json")
    for sensor in field["sensors"]:
        sensor["noise"] = 0
    database = Database(directory / "sim.db")
    database.initialize(field)
    simulator = FieldSimulator(database, field, tick_wall_seconds=1.0)
    return simulator, database, field


def zone_average(snapshot, zone_id):
    return next(zone["average"] for zone in snapshot["zones"] if zone["id"] == zone_id)


def raw_moisture(simulator, sensor_id):
    return next(sensor.moisture for sensor in simulator.sensors if sensor.id == sensor_id)


class MoistureTests(unittest.TestCase):
    def test_open_valve_adds_water_and_a_closed_valve_dries(self):
        rng = random.Random(0)
        closed = advance_moisture(
            40, valve_open=False, dt_hours=1, dry_rate=2, irrigate_rate=30, noise=0, rng=rng
        )
        opened = advance_moisture(
            40, valve_open=True, dt_hours=1, dry_rate=2, irrigate_rate=30, noise=0, rng=rng
        )
        self.assertEqual(closed, 38)
        self.assertEqual(opened, 68)


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.sim, self.db, self.field = build(Path(self.temp.name))

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_irrigation_raises_one_zone_while_the_others_dry(self):
        before = self.sim.snapshot()
        self.sim.set_valve("zone1", True, "test")
        opened = self.sim.zones["zone1"].opened_wall
        after = self.sim.step(
            dt_sim_seconds=3600,
            now=opened + timedelta(seconds=30),
            persist=False,
        )
        self.assertGreater(zone_average(after, "zone1"), zone_average(before, "zone1") + 20)
        self.assertLess(zone_average(after, "zone2"), zone_average(before, "zone2"))
        zone = next(item for item in after["zones"] if item["id"] == "zone1")
        if zone["average"] >= zone["target_moisture"]:
            self.assertFalse(zone["valve_open"])
            self.assertEqual(zone["last_stop_reason"], "target_reached")
        else:
            self.assertTrue(zone["valve_open"])

    def test_safety_timer_closes_the_valve_without_inventing_litres(self):
        self.sim.set_valve("zone1", True, "test")
        opened = self.sim.zones["zone1"].opened_wall
        still_open = self.sim.step(dt_sim_seconds=1, now=opened + timedelta(seconds=599), persist=False)
        self.assertTrue(next(zone["valve_open"] for zone in still_open["zones"] if zone["id"] == "zone1"))
        closed = self.sim.step(dt_sim_seconds=1, now=opened + timedelta(seconds=600), persist=False)
        zone = next(item for item in closed["zones"] if item["id"] == "zone1")
        self.assertFalse(zone["valve_open"])
        self.assertEqual(zone["last_stop_reason"], "max_duration")
        event = self.db.recent_events(1)[0]
        self.assertEqual(event["stop_reason"], "max_duration")
        self.assertIsNone(event["estimated_liters"])
        self.assertGreaterEqual(event["duration_sec"], 600)

    def test_emergency_stop_latches_until_reset(self):
        self.sim.set_valve("zone1", True, "test")
        stopped = self.sim.emergency_stop()
        self.assertTrue(stopped["emergency_stop"])
        self.assertFalse(any(zone["valve_open"] for zone in stopped["zones"]))
        with self.assertRaises(SafetyError):
            self.sim.set_valve("zone1", True, "test")
        self.sim.reset_emergency()
        self.assertFalse(self.sim.zones["zone1"].valve_open)
        self.sim.set_valve("zone1", True, "test")
        self.assertTrue(self.sim.zones["zone1"].valve_open)

    def test_a_dry_zone_opens_and_stays_off_during_cooldown(self):
        opened = self.sim.step(dt_sim_seconds=1, persist=False)
        zone1 = next(item for item in opened["zones"] if item["id"] == "zone1")
        zone2 = next(item for item in opened["zones"] if item["id"] == "zone2")
        self.assertTrue(zone1["valve_open"])
        self.assertEqual(self.db.recent_events(1)[0]["reason"], "dry_soil")
        self.assertFalse(zone2["valve_open"])
        self.sim.set_valve("zone1", False, "test")
        closed_at = self.sim.zones["zone1"].last_closed_wall
        held = self.sim.step(dt_sim_seconds=1, now=closed_at + timedelta(seconds=10), persist=False)
        zone = next(item for item in held["zones"] if item["id"] == "zone1")
        self.assertFalse(zone["valve_open"])

    def test_two_missing_sensors_blank_the_zone_average(self):
        self.sim.set_sensor_failed("zone1-s1", True)
        self.sim.set_sensor_failed("zone1-s2", True)
        snapshot = self.sim.snapshot()
        zone = next(item for item in snapshot["zones"] if item["id"] == "zone1")
        sensor = next(item for item in snapshot["sensors"] if item["id"] == "zone1-s2")
        self.assertEqual(zone["status"], "insufficient")
        self.assertIsNone(zone["average"])
        self.assertEqual(sensor["quality"], "missing")
        self.assertTrue(any(alert["code"] == "zone1:insufficient" for alert in snapshot["alerts"]))

    def test_restart_continues_from_the_saved_soil_value(self):
        initial = next(sensor["initial_moisture"] for sensor in self.field["sensors"] if sensor["id"] == "zone2-s1")
        self.sim.step(dt_sim_seconds=3600, now=self.sim.started_wall + timedelta(seconds=10), persist=True)
        dried = round(raw_moisture(self.sim, "zone2-s1"), 2)
        restarted = FieldSimulator(self.db, self.field, tick_wall_seconds=1.0)
        self.assertAlmostEqual(raw_moisture(restarted, "zone2-s1"), dried, places=2)
        self.assertLess(dried, initial - 1)
        self.assertFalse(any(zone.valve_open for zone in restarted.zones.values()))


if __name__ == "__main__":
    unittest.main()
