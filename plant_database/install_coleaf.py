"""Unpack CoLeaf DATASET.zip into the plant database.

The zip holds about 1,000 coffee-leaf photos in 10 groups:
eight single nutrients, healthy leaves, and a mixed group.
Run this once from the Kshetra folder:

    py -3 plant_database/install_coleaf.py

On macOS or Linux, use python3 instead of py -3.
"""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.vision.catalog import load_catalog

OUTER_ZIP = ROOT / "CoLeaf DATASET.zip"
SOURCE = ROOT / "data" / "coleaf_src"
ENTRIES = ROOT / "plant_database" / "entries"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

# archive name inside the outer zip, entry folder, treatment word or None
GROUPS = (
    ("healthy.zip", "healthy", None),
    ("boron-B.zip", "boron", "boron"),
    ("calcium-Ca.zip", "calcium", "calcium"),
    ("iron-Fe.zip", "iron", "iron"),
    ("magnesium-Mg.zip", "magnesium", "magnesium"),
    ("manganese-Mn.zip", "manganese", "manganese"),
    ("nitrogen-N.zip", "nitrogen", "nitrogen"),
    ("phosphorus-P.zip", "phosphorus", "phosphorus"),
    ("potasium-K.zip", "potassium", "potassium"),
    ("more-deficiencies.zip", "multiple", None),
)


def main() -> None:
    if not OUTER_ZIP.exists():
        raise SystemExit(f"Put the CoLeaf zip here: {OUTER_ZIP}")
    _unpack_outer()
    retired = ("sulfur", "pest")
    for name in retired:
        folder = ENTRIES / name
        if folder.exists():
            shutil.rmtree(folder)
    total = 0
    for archive_name, entry_id, treatment in GROUPS:
        archive = _find_archive(archive_name)
        count = _install_group(archive, entry_id, treatment)
        total += count
        print(f"{entry_id}: {count} photos")
    print(f"Installed {total} CoLeaf photos.")
    load_catalog(ROOT / "plant_database")
    print("Color index is ready.")
    if SOURCE.exists():
        shutil.rmtree(SOURCE)


def _unpack_outer() -> None:
    needed = SOURCE / "CoLeaf DATASET"
    if needed.is_dir() and any(needed.glob("*.zip")):
        return
    SOURCE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTER_ZIP) as outer:
        outer.extractall(SOURCE)


def _find_archive(name: str) -> Path:
    matches = list(SOURCE.rglob(name))
    if not matches:
        raise SystemExit(f"The CoLeaf zip has no {name}.")
    return matches[0]


def _install_group(archive: Path, entry_id: str, treatment: str | None) -> int:
    folder = ENTRIES / entry_id
    examples = folder / "examples"
    if examples.exists():
        shutil.rmtree(examples)
    examples.mkdir(parents=True)
    (folder / "entry.json").write_text(json.dumps(_spec(entry_id, treatment), indent=2) + "\n", encoding="utf-8")
    count = 0
    with zipfile.ZipFile(archive) as inner:
        for member in inner.infolist():
            if member.is_dir():
                continue
            suffix = Path(member.filename).suffix.lower()
            if suffix not in IMAGE_SUFFIXES:
                continue
            target = examples / Path(member.filename).name
            target.write_bytes(inner.read(member))
            count += 1
    return count


def _spec(entry_id: str, treatment: str | None) -> dict:
    if entry_id == "healthy":
        return {
            "id": "healthy",
            "kind": "healthy",
            "title": "Looks like the healthy examples",
            "farmer_message": "This photo is closest to the healthy pictures in the CoLeaf set. No nutrient treatment is suggested.",
            "recommended_action": "Keep watching the plant. This computer does not control the field.",
            "treatment_id": None,
            "dose_seconds": 30,
        }
    if entry_id == "multiple":
        return {
            "id": "multiple",
            "kind": "deficiency",
            "title": "Possible mix of deficiencies",
            "farmer_message": "This photo is closest to the combined-deficiency examples in the CoLeaf set. Those pictures show more than one nutrient problem at once, so the match does not name a single nutrient.",
            "recommended_action": "Look at the plant in person. This computer does not control the field.",
            "treatment_id": None,
            "dose_seconds": 30,
        }
    nutrient = treatment or entry_id
    return {
        "id": entry_id,
        "kind": "deficiency",
        "title": f"Possible {nutrient} deficiency",
        "farmer_message": (
            f"This photo is closest to the {nutrient} examples in the CoLeaf set. "
            "That is a visual match to those pictures, not a measurement of the nutrient in the leaf or the soil."
        ),
        "recommended_action": "This computer only names the closest example. It does not control the field.",
        "treatment_id": nutrient,
        "dose_seconds": 30,
    }


if __name__ == "__main__":
    main()
