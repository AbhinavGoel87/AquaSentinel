"""Doctor matching and the irrigation-tank confirmation gate."""

import io
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from backend.vision.advisor import advise
from backend.vision.catalog import load_catalog
from backend.vision.features import features_from_bytes
from backend.vision.pngutil import write_rgb_png
from tests.support import ROOT, make_app


def solid(path: Path, color: tuple[int, int, int]) -> None:
    write_rgb_png(path, 24, 24, lambda x, y, w, h: color)


class AdvisorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(ROOT / "plant_database")

    def test_green_matches_healthy_and_cannot_treat(self):
        advice = self._advice((48, 150, 55))
        self.assertEqual(advice["entry_id"], "healthy")
        self.assertFalse(advice["can_treat"])
        self.assertEqual(advice["method"], "database-color-match")

    def test_yellow_matches_magnesium(self):
        advice = self._advice((210, 160, 40))
        self.assertEqual(advice["entry_id"], "magnesium")
        self.assertEqual(advice["kind"], "deficiency")
        self.assertTrue(advice["can_treat"])

    def test_a_dark_photo_stays_uncertain(self):
        advice = self._advice((4, 4, 4))
        self.assertEqual(advice["kind"], "uncertain")
        self.assertFalse(advice["can_treat"])

    def _advice(self, color):
        folder = Path(tempfile.mkdtemp())
        path = folder / "leaf.png"
        solid(path, color)
        return advise(features_from_bytes(path.read_bytes()), self.catalog)


class TreatmentApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = make_app(Path(self.temp.name))
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions["db"].close()
        self.temp.cleanup()

    def test_upload_is_marked_simulated_and_uncertain_cannot_start_a_treatment(self):
        dark = self._png((4, 4, 4))
        report = self.client.post(
            "/api/inspections",
            data={"image": (dark, "leaf.png"), "source": "simulated", "rover_id": "rover1"},
        )
        self.assertEqual(report.status_code, 200)
        body = report.get_json()
        self.assertEqual(body["kind"], "uncertain")
        refused = self.client.post("/api/treatments/confirm", json={"report_id": body["report_id"]})
        self.assertEqual(refused.status_code, 409)
        self.assertFalse(self.client.get("/api/outputs").get_json()["treatment"])

    def test_confirm_starts_a_timed_cycle_and_emergency_stop_ends_it(self):
        yellow = self._png((210, 160, 40))
        report = self.client.post(
            "/api/inspections",
            data={"image": (yellow, "leaf.png"), "source": "simulated", "rover_id": "rover1"},
        )
        body = report.get_json()
        self.assertEqual(body["entry_id"], "magnesium")
        confirmed = self.client.post("/api/treatments/confirm", json={"report_id": body["report_id"]})
        self.assertEqual(confirmed.status_code, 200)
        treatment = confirmed.get_json()["treatment"]
        self.assertTrue(treatment["active"])
        self.assertEqual(treatment["treatment_id"], "magnesium")
        outputs = self.client.get("/api/outputs").get_json()
        self.assertEqual(outputs["treatment"]["id"], "magnesium")
        stopped = self.client.post("/api/emergency-stop")
        self.assertIsNone(stopped.get_json()["treatment"]["treatment_id"])
        self.assertFalse(stopped.get_json()["treatment"]["active"])

    def test_the_cycle_ends_when_its_time_is_up(self):
        yellow = self._png((210, 160, 40))
        report = self.client.post(
            "/api/inspections",
            data={"image": (yellow, "leaf.png"), "source": "simulated"},
        ).get_json()
        self.client.post("/api/treatments/confirm", json={"report_id": report["report_id"]})
        treatments = self.app.extensions["treatments"]
        started = treatments.active["started"]
        treatments.tick(started + timedelta(seconds=report["dose_seconds"]), False)
        self.assertFalse(treatments.public()["active"])

    def _png(self, color):
        folder = Path(self.temp.name)
        path = folder / "upload.png"
        solid(path, color)
        return io.BytesIO(path.read_bytes())


if __name__ == "__main__":
    unittest.main()
