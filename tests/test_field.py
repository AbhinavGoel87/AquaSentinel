"""Exhibition field file."""

import unittest

from backend.simulation.layout import FieldConfigError, load_field, validate_field
from tests.support import ROOT


class FieldTests(unittest.TestCase):
    def test_exhibition_field_has_two_zones_and_a_center_road(self):
        field = load_field(ROOT / "data" / "field.json")
        self.assertEqual(len(field["zones"]), 2)
        self.assertEqual(len(field["sensors"]), 6)
        self.assertEqual([route["rover_id"] for route in field["routes"]], ["rover1"])
        ordered = sorted(field["zones"], key=lambda zone: zone["bounds"]["x"])
        left, right = ordered[0]["bounds"], ordered[1]["bounds"]
        road = field["road"]
        self.assertLessEqual(left["x"] + left["w"], road["x"])
        self.assertLessEqual(road["x"] + road["w"], right["x"])
        dock = field["routes"][0]["dock"]
        self.assertTrue(road["x"] <= dock["x"] <= road["x"] + road["w"])

    def test_a_second_rover_is_rejected(self):
        field = load_field(ROOT / "data" / "field.json")
        extra = dict(field["routes"][0])
        extra["id"] = "route-east"
        extra["rover_id"] = "rover2"
        field["routes"].append(extra)
        with self.assertRaises(FieldConfigError):
            validate_field(field)


if __name__ == "__main__":
    unittest.main()
