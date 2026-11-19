"""HTTP API for the plant doctor page."""

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

    def test_page_is_the_doctor_and_leaves_the_field_out(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.data.decode("utf-8")
        self.assertIn("Kshetra", page)
        self.assertIn("Doctor", page)
        self.assertNotIn('id="tab-field"', page)
        self.assertNotIn("Open sprinkler", page)
        self.assertNotIn("Add to irrigation tank", page)

    def test_field_controls_are_not_part_of_this_build(self):
        self.assertEqual(self.client.get("/api/field").status_code, 404)
        self.assertEqual(self.client.get("/api/outputs").status_code, 404)
        self.assertEqual(self.client.post("/api/zones/zone1/valve", json={"open": True}).status_code, 404)
        self.assertEqual(self.client.post("/api/emergency-stop").status_code, 404)

    def test_doctor_waits_until_a_photo_arrives(self):
        response = self.client.get("/api/doctor")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIsNone(body["report"])
        self.assertIn("photo", body["note"].lower())


if __name__ == "__main__":
    unittest.main()
