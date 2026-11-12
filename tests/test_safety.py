"""Valve safety rules."""

import unittest

from backend.irrigation.safety import open_is_allowed, valve_should_force_close


class SafetyTests(unittest.TestCase):
    def test_emergency_stop_refuses_a_new_open(self):
        allowed, message = open_is_allowed(True)
        self.assertFalse(allowed)
        self.assertIn("Emergency stop", message)
        self.assertTrue(open_is_allowed(False)[0])

    def test_limit_uses_wall_clock_seconds(self):
        self.assertEqual(valve_should_force_close(599, 600, False), (False, None))
        self.assertEqual(valve_should_force_close(600, 600, False), (True, "max_duration"))

    def test_emergency_wins_over_the_timer(self):
        self.assertEqual(valve_should_force_close(0, 600, True), (True, "emergency_stop"))


if __name__ == "__main__":
    unittest.main()
