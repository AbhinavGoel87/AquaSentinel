"""Zone health rules."""

import unittest

from backend.sensors.health import judge_zone


RULES = {
    "min_sensors": 2,
    "suspect_gap": 20,
    "neighbor_agreement": 10,
    "uneven_spread": 15,
}


def judge(samples):
    return judge_zone(samples, **RULES)


class HealthTests(unittest.TestCase):
    def test_outlier_is_excluded_when_the_other_two_agree(self):
        zone = judge([("s1", 30), ("s2", 32), ("s3", 70)])
        qualities = {item.sensor_id: item.quality for item in zone.sensors}
        self.assertEqual(qualities["s3"], "suspect")
        self.assertEqual(zone.average, 31)
        self.assertEqual(zone.status, "ok")
        self.assertEqual(zone.included_count, 2)

    def test_wide_but_even_spread_stays_in_the_average(self):
        zone = judge([("s1", 30), ("s2", 50), ("s3", 70)])
        self.assertTrue(all(item.quality == "ok" for item in zone.sensors))
        self.assertEqual(zone.status, "uneven")
        self.assertEqual(zone.average, 50)

    def test_one_reading_is_not_a_zone_average(self):
        zone = judge([("s1", None), ("s2", None), ("s3", 40)])
        self.assertEqual(zone.status, "insufficient")
        self.assertIsNone(zone.average)
        self.assertEqual(zone.sensors[2].quality, "ok")

    def test_out_of_range_reading_is_rejected(self):
        zone = judge([("s1", 120), ("s2", 40), ("s3", 42)])
        self.assertEqual(zone.sensors[0].quality, "invalid")
        self.assertEqual(zone.status, "ok")
        self.assertEqual(zone.average, 41)


if __name__ == "__main__":
    unittest.main()
