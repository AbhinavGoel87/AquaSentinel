"""Message shapes reserved for later hardware."""

import unittest

from backend.communication.schemas import (
    validate_rover_status,
    validate_sensor_report,
    validate_valve_command,
)
from backend.communication.topics import (
    INSPECTION_UPLOAD_PATH,
    irrigation_topic,
    sensor_topic,
)


def sensor_message(**overrides):
    message = {
        "device_id": "esp32-zone1",
        "source": "simulated",
        "ts": "2026-11-11T12:00:00Z",
        "seq": 1,
        "zone_id": "zone1",
        "readings": [{"sensor_id": "zone1-s1", "moisture_pct": 34.2, "ok": True}],
    }
    message.update(overrides)
    return message


class SchemaTests(unittest.TestCase):
    def test_sensor_report_accepts_the_documented_shape(self):
        self.assertEqual(validate_sensor_report(sensor_message()), [])

    def test_boolean_is_not_a_sequence_number(self):
        errors = validate_sensor_report(sensor_message(seq=True))
        self.assertTrue(any("seq" in error for error in errors))

    def test_failed_reading_has_no_moisture_number(self):
        good = sensor_message(readings=[{"sensor_id": "zone1-s1", "moisture_pct": None, "ok": False}])
        bad = sensor_message(readings=[{"sensor_id": "zone1-s1", "moisture_pct": 10, "ok": False}])
        over = sensor_message(readings=[{"sensor_id": "zone1-s1", "moisture_pct": 101, "ok": True}])
        self.assertEqual(validate_sensor_report(good), [])
        self.assertTrue(validate_sensor_report(bad))
        self.assertTrue(validate_sensor_report(over))

    def test_valve_command_limit_is_a_real_integer(self):
        command = {
            "command_id": "cmd-1",
            "device_id": "pi-controller",
            "ts": "2026-11-11T12:00:00Z",
            "zone_id": "zone1",
            "valve": "open",
            "mode": "manual",
            "max_seconds": 600,
        }
        self.assertEqual(validate_valve_command(command), [])
        self.assertTrue(validate_valve_command({**command, "max_seconds": True}))
        self.assertTrue(validate_valve_command({**command, "max_seconds": 0}))

    def test_rover_state_names_are_fixed(self):
        status = {
            "device_id": "rover1",
            "source": "simulated",
            "ts": "2026-11-11T12:00:00Z",
            "seq": 4,
            "state": "idle",
            "battery_pct": 80,
            "camera_ok": True,
            "link_ok": True,
            "route_id": "route-west",
            "checkpoint_id": None,
        }
        self.assertEqual(validate_rover_status(status), [])
        self.assertTrue(validate_rover_status({**status, "state": "flying"}))

    def test_topics_match_the_contract(self):
        self.assertEqual(sensor_topic("zone1"), "kshetra/sensors/zone1")
        self.assertEqual(irrigation_topic("zone2"), "kshetra/irrigation/zone2")
        self.assertEqual(INSPECTION_UPLOAD_PATH, "/api/inspections")
        with self.assertRaises(ValueError):
            sensor_topic("zone 1")


if __name__ == "__main__":
    unittest.main()
