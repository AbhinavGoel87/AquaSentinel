"""The plant database lives in a folder the farmer can edit.

Each entry is a directory with entry.json and an examples folder of photos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from backend.vision.features import features_from_bytes

KINDS = ("healthy", "deficiency", "disease", "discrepancy")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_DOSE_SECONDS = 180


class PlantDatabaseError(ValueError):
    """The uploaded plant database is missing a required fact."""


@dataclass
class ExamplePhoto:
    path: Path
    features: dict


@dataclass
class PlantEntry:
    id: str
    kind: str
    title: str
    farmer_message: str
    recommended_action: str
    treatment_id: str | None
    dose_seconds: int
    examples: list[ExamplePhoto] = field(default_factory=list)


def load_catalog(root: Path) -> list[PlantEntry]:
    entries_dir = Path(root) / "entries"
    if not entries_dir.is_dir():
        raise PlantDatabaseError(f"Put plant entries in {entries_dir}")
    entries = []
    for directory in sorted(path for path in entries_dir.iterdir() if path.is_dir()):
        spec_path = directory / "entry.json"
        if not spec_path.exists():
            continue
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        entries.append(_entry(directory, spec))
    if not entries:
        raise PlantDatabaseError("The plant database has no entries.")
    ids = [entry.id for entry in entries]
    if len(ids) != len(set(ids)):
        raise PlantDatabaseError("Plant entry ids must be unique.")
    return entries


def _entry(directory: Path, spec: dict) -> PlantEntry:
    entry_id = _text(spec.get("id"), f"{directory.name} id")
    kind = spec.get("kind")
    if kind not in KINDS:
        raise PlantDatabaseError(f"{entry_id} kind must be one of {', '.join(KINDS)}.")
    title = _text(spec.get("title"), f"{entry_id} title")
    message = _text(spec.get("farmer_message"), f"{entry_id} farmer_message")
    action = _text(spec.get("recommended_action"), f"{entry_id} recommended_action")
    treatment = spec.get("treatment_id")
    if treatment is not None and (not isinstance(treatment, str) or not treatment.strip()):
        raise PlantDatabaseError(f"{entry_id} treatment_id must be a word or null.")
    dose = spec.get("dose_seconds", 30)
    if isinstance(dose, bool) or not isinstance(dose, int) or dose < 1:
        raise PlantDatabaseError(f"{entry_id} dose_seconds must be a positive integer.")
    dose = min(dose, MAX_DOSE_SECONDS)
    if kind in ("deficiency", "disease") and treatment and "irrigation" not in action.lower():
        raise PlantDatabaseError(
            f"{entry_id} must tell the farmer the treatment goes into the irrigation water."
        )
    examples = []
    examples_dir = directory / "examples"
    if examples_dir.is_dir():
        for path in sorted(examples_dir.iterdir()):
            if path.suffix.lower() not in IMAGE_SUFFIXES or not path.is_file():
                continue
            examples.append(ExamplePhoto(path=path, features=features_from_bytes(path.read_bytes())))
    return PlantEntry(
        id=entry_id,
        kind=kind,
        title=title,
        farmer_message=message,
        recommended_action=action,
        treatment_id=treatment.strip() if isinstance(treatment, str) else None,
        dose_seconds=dose,
        examples=examples,
    )


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlantDatabaseError(f"{label} must be a non-empty string.")
    return value.strip()
