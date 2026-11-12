"""HTTP API for the Phase 1 field page."""

import tempfile
import unittest
from pathlib import Path

from tests.support import make_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = make_app(Path(self.temp.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions["db"].close()
        self.temp.cleanup()

    def test_field_is_marked_simulated_and_starts_closed(self):
        response = self.client.get("/api/field")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["source"], "simulated")
        self.assertFalse(body["hardware_connected"])
        self.assertIn("Simulated", body["disclaimer"])
        self.assertIn("demo settings", body["model_note"])
        self.assertIn("does not invent", body["water_note"])
        self.assertEqual(len(body["sensors"]), 6)
        self.assertEqual(len(body["zones"]), 2)
        self.assertLess(body["road"]["x"], body["routes"][0]["dock"]["x"])
        self.assertFalse(any(zone["valve_open"] for zone in body["zones"]))
        self.assertTrue(all(rover["status"] == "parked" for rover in body["rovers"]))

    def test_page_names_the_simulation(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AquaSentinel", response.data)
        self.assertIn(b"Simulated", response.data)
        self.assertIn(b'role="tablist"', response.data)
        self.assertIn(b"Doctor", response.data)

    def test_emergency_stop_blocks_the_next_open(self):
        opened = self.client.post("/api/zones/zone1/valve", json={"open": True})
        self.assertEqual(opened.status_code, 200)
        self.assertTrue(opened.get_json()["zones"][0]["valve_open"])
        stopped = self.client.post("/api/emergency-stop")
        self.assertTrue(stopped.get_json()["emergency_stop"])
        self.assertFalse(any(zone["valve_open"] for zone in stopped.get_json()["zones"]))
        refused = self.client.post("/api/zones/zone1/valve", json={"open": True})
        self.assertEqual(refused.status_code, 409)
        self.client.post("/api/emergency-stop/reset")
        reopened = self.client.post("/api/zones/zone1/valve", json={"open": True})
        self.assertEqual(reopened.status_code, 200)

    def test_bad_valve_request_and_unknown_zone(self):
        self.assertEqual(self.client.post("/api/zones/zone1/valve", json={"open": "yes"}).status_code, 400)
        self.assertEqual(self.client.post("/api/zones/zone9/valve", json={"open": True}).status_code, 404)

    def test_fault_injection_removes_a_reading(self):
        response = self.client.post("/api/simulation/sensors/zone1-s1/fault", json={"failed": True})
        self.assertEqual(response.status_code, 200)
        sensor = next(item for item in response.get_json()["sensors"] if item["id"] == "zone1-s1")
        self.assertEqual(sensor["quality"], "missing")
        self.assertTrue(sensor["failed"])
        self.assertEqual(sensor["source"], "simulated")

    def test_restart_closes_a_valve_that_was_left_open(self):
        self.client.post("/api/zones/zone1/valve", json={"open": True})
        self.app.extensions["db"].close()
        restarted = make_app(Path(self.temp.name))
        snapshot = restarted.extensions["sim"].snapshot()
        self.assertFalse(any(zone["valve_open"] for zone in snapshot["zones"]))
        event = restarted.extensions["db"].recent_events(1)[0]
        self.assertEqual(event["stop_reason"], "startup_safe_state")
        self.assertIsNone(event["estimated_liters"])
        restarted.extensions["db"].close()


if __name__ == "__main__":
    unittest.main()
