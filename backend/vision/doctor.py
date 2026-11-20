"""Receive a rover photo, compare it with the plant database, and remember the result."""

from __future__ import annotations

import json
from pathlib import Path

from backend.database.db import Database
from backend.utils.timeutil import utc_iso, utc_now
from backend.vision.advisor import advise
from backend.vision.catalog import PlantEntry
from backend.vision.features import features_from_bytes

MAX_BYTES = 15_000_000


class DoctorService:
    def __init__(self, db: Database, catalog: list[PlantEntry], inbox: Path):
        self.db = db
        self.catalog = catalog
        self.inbox = Path(inbox)
        self.inbox.mkdir(parents=True, exist_ok=True)

    def examine(self, payload: bytes, rover_id: str, checkpoint_id: str | None, source: str) -> dict:
        if not payload:
            raise ValueError("The photo was empty.")
        if len(payload) > MAX_BYTES:
            raise ValueError("The photo is larger than 5 MB.")
        suffix = _suffix(payload)
        features = features_from_bytes(payload)
        advice = advise(features, self.catalog)
        created = utc_now()
        filename = created.strftime("%Y%m%dT%H%M%S%f") + suffix
        path = self.inbox / filename
        path.write_bytes(payload)
        inspection_id = self.db.insert_inspection(
            rover_id or "rover1",
            checkpoint_id,
            str(path),
            utc_iso(created),
            source,
        )
        report_id = self.db.insert_report(inspection_id, advice, utc_iso(created))
        report = dict(advice)
        report.update(
            {
                "report_id": report_id,
                "inspection_id": inspection_id,
                "rover_id": rover_id or "rover1",
                "checkpoint_id": checkpoint_id,
                "image_url": f"/api/inspections/{inspection_id}/image",
                "created_at": utc_iso(created),
                "honesty": "Sureness is how close the colors are to each entry. It is not a laboratory test.",
            }
        )
        return report

    def public(self) -> dict:
        row = self.db.latest_report()
        if row is None:
            return {
                "report": None,
                "note": "No photo yet. The camera can send one, or you can choose a file here.",
            }
        report = {
            "report_id": row["report_id"],
            "inspection_id": row["inspection_id"],
            "entry_id": row["entry_id"],
            "kind": row["kind"],
            "title": row["title"],
            "farmer_message": row["farmer_message"],
            "recommended_action": row["recommended_action"],
            "treatment_id": row["treatment_id"],
            "dose_seconds": row["dose_seconds"],
            "match_score": row["match_score"],
            "matches": _matches(row["matches_json"]),
            "method": row["method"],
            "can_treat": row["kind"] in ("deficiency", "disease") and bool(row["treatment_id"]),
            "rover_id": row["rover_id"],
            "checkpoint_id": row["checkpoint_id"],
            "image_url": f"/api/inspections/{row['inspection_id']}/image",
            "created_at": row["created_at"],
            "honesty": "Sureness is how close the colors are to each entry. It is not a laboratory test.",
        }
        return {"report": report, "note": report["honesty"]}

    def image_path(self, inspection_id: int) -> Path | None:
        stored = self.db.inspection_path(inspection_id)
        if stored is None:
            return None
        path = Path(stored)
        if not path.exists():
            return None
        return path


def _matches(stored) -> list:
    if not stored:
        return []
    try:
        payload = json.loads(stored)
    except (TypeError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def _suffix(payload: bytes) -> str:
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if payload.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    raise ValueError("Send a PNG or JPEG photo.")
