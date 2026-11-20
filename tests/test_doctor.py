"""Doctor matching and the irrigation-tank confirmation gate."""

import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from backend.vision.advisor import advise
from backend.vision.catalog import load_catalog
from backend.vision.features import features_from_bytes
from backend.vision.pngutil import write_rgb_png
from tests.support import ROOT, make_app


def _example(entry_id: str) -> Path:
    folder = ROOT / "plant_database" / "entries" / entry_id / "examples"
    photos = [
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.stat().st_size < 5_000_000
    ]
    if not photos:
        raise unittest.SkipTest(f"No CoLeaf photo installed for {entry_id}.")
    return sorted(photos)[0]


def solid(path: Path, color: tuple[int, int, int]) -> None:
    write_rgb_png(path, 24, 24, lambda x, y, w, h: color)


class AdvisorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(ROOT / "plant_database")

    def test_coleaf_has_ten_groups_and_about_a_thousand_photos(self):
        photos = sum(len(entry.examples) for entry in self.catalog)
        self.assertGreaterEqual(photos, 900)
        self.assertEqual(
            {entry.id for entry in self.catalog},
            {
                "healthy", "boron", "calcium", "iron", "magnesium", "manganese",
                "nitrogen", "phosphorus", "potassium", "multiple",
            },
        )

    def test_a_known_magnesium_photo_can_be_treated(self):
        path = _example("magnesium")
        advice = advise(features_from_bytes(path.read_bytes()), self.catalog)
        self.assertEqual(advice["entry_id"], "magnesium")
        self.assertEqual(advice["kind"], "deficiency")
        self.assertTrue(advice["can_treat"])
        self.assertEqual(advice["method"], "database-color-match")
        self.assertGreaterEqual(len(advice["matches"]), 9)
        self.assertEqual(advice["matches"][0]["entry_id"], "magnesium")
        self.assertEqual(advice["matches"][0]["sureness"], 100)
        self.assertNotIn("too close", advice["farmer_message"].lower())

    def test_a_yellow_magnesium_leaf_is_not_called_healthy(self):
        magnesium = next(entry for entry in self.catalog if entry.id == "magnesium")
        yellow = [example for example in magnesium.examples if example.features.get("pale", 0) > 0.20]
        self.assertGreaterEqual(len(yellow), 20)
        for example in yellow:
            held = []
            for entry in self.catalog:
                if entry.id != "magnesium":
                    held.append(entry)
                    continue
                kept = [item for item in entry.examples if item.path != example.path]
                held.append(replace(entry, examples=kept))
            advice = advise(example.features, held)
            self.assertNotEqual(advice["kind"], "healthy", example.path.name)
            self.assertNotEqual(advice["kind"], "uncertain", example.path.name)
            self.assertGreater(len(advice["matches"]), 1)

    def test_healthy_examples_stay_healthy(self):
        healthy = next(entry for entry in self.catalog if entry.id == "healthy")
        for example in healthy.examples:
            self.assertLessEqual(example.features["pale"], 0.10)
            advice = advise(example.features, self.catalog)
            self.assertEqual(advice["entry_id"], "healthy", example.path.name)
            self.assertFalse(advice["can_treat"])

    def test_the_mixed_group_cannot_start_a_treatment(self):
        multiple = next(entry for entry in self.catalog if entry.id == "multiple")
        self.assertIsNone(multiple.treatment_id)

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

    def test_raw_jpeg_body_is_classified(self):
        sample = _example("magnesium")
        payload = sample.read_bytes()
        report = self.client.post("/api/inspections", data=payload, content_type="image/jpeg")
        self.assertEqual(report.status_code, 200)
        body = report.get_json()
        self.assertEqual(body["entry_id"], "magnesium")
        self.assertEqual(body["kind"], "deficiency")
        self.assertEqual(body["method"], "database-color-match")
        self.assertGreaterEqual(len(body["matches"]), 9)
        saved = self.client.get("/api/doctor").get_json()["report"]
        self.assertEqual(saved["matches"][0]["entry_id"], "magnesium")
        self.assertIn("not a laboratory test", body["honesty"])
        self.assertEqual(body["rover_id"], "rover1")
        image = self.client.get(body["image_url"])
        try:
            self.assertEqual(image.status_code, 200)
            self.assertTrue(image.data.startswith(b"\xff\xd8\xff"))
            self.assertEqual(image.data, payload)
        finally:
            image.close()

    def test_upload_is_marked_simulated_and_stays_uncertain(self):
        dark = self._png((4, 4, 4))
        report = self.client.post(
            "/api/inspections",
            data={"image": (dark, "leaf.png"), "source": "simulated", "rover_id": "rover1"},
        )
        self.assertEqual(report.status_code, 200)
        body = report.get_json()
        self.assertEqual(body["kind"], "uncertain")
        self.assertFalse(body["can_treat"])
        latest = self.client.get("/api/doctor").get_json()
        self.assertEqual(latest["report"]["kind"], "uncertain")

    def _png(self, color):
        folder = Path(self.temp.name)
        path = folder / "upload.png"
        solid(path, color)
        return io.BytesIO(path.read_bytes())


if __name__ == "__main__":
    unittest.main()
