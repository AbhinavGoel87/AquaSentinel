"""The plant database lives in a folder the farmer can edit.

Each entry is a directory with entry.json and an examples folder of photos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from backend.vision.features import FEATURE_VERSION, features_from_bytes

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
    root = Path(root)
    entries_dir = root / "entries"
    if not entries_dir.is_dir():
        raise PlantDatabaseError(f"Put plant entries in {entries_dir}")
    cache_path = root / ".feature_cache.json"
    cache = _read_cache(cache_path)
    seen: set[str] = set()
    dirty = False
    entries = []
    for directory in sorted(path for path in entries_dir.iterdir() if path.is_dir()):
        spec_path = directory / "entry.json"
        if not spec_path.exists():
            continue
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        entry, changed = _entry(directory, spec, cache, seen)
        dirty = dirty or changed
        entries.append(entry)
    if not entries:
        raise PlantDatabaseError("The plant database has no entries.")
    ids = [entry.id for entry in entries]
    if len(ids) != len(set(ids)):
        raise PlantDatabaseError("Plant entry ids must be unique.")
    for key in list(cache):
        if key not in seen:
            cache.pop(key, None)
            dirty = True
    if dirty:
        _write_cache(cache_path, cache)
    return entries


def _entry(directory: Path, spec: dict, cache: dict, seen: set[str]) -> tuple[PlantEntry, bool]:
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
    changed = False
    examples_dir = directory / "examples"
    if examples_dir.is_dir():
        for path in sorted(examples_dir.iterdir()):
            if path.suffix.lower() not in IMAGE_SUFFIXES or not path.is_file():
                continue
            features, fresh = _cached_features(path, cache, seen)
            changed = changed or fresh
            examples.append(ExamplePhoto(path=path, features=features))
    return PlantEntry(
        id=entry_id,
        kind=kind,
        title=title,
        farmer_message=message,
        recommended_action=action,
        treatment_id=treatment.strip() if isinstance(treatment, str) else None,
        dose_seconds=dose,
        examples=examples,
    ), changed


def _cached_features(path: Path, cache: dict, seen: set[str]) -> tuple[dict, bool]:
    key = str(path.resolve())
    seen.add(key)
    stat = path.stat()
    saved = cache.get(key)
    if (
        saved
        and saved.get("version") == FEATURE_VERSION
        and saved.get("size") == stat.st_size
        and saved.get("mtime_ns") == stat.st_mtime_ns
    ):
        return saved["features"], False
    features = features_from_bytes(path.read_bytes())
    cache[key] = {
        "version": FEATURE_VERSION,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "features": features,
    }
    return features, True


def _read_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _write_cache(path: Path, cache: dict) -> None:
    path.write_text(json.dumps(cache), encoding="utf-8")


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlantDatabaseError(f"{label} must be a non-empty string.")
    return value.strip()
