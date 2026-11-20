"""A farmer's choice of deficiency, recorded on this computer.

There is no timer. The record does not open a valve or talk to the Arduino Uno.
"""

from __future__ import annotations

import threading

from backend.database.db import Database
from backend.irrigation.safety import SafetyError
from backend.utils.timeutil import utc_iso, utc_now
from backend.vision.catalog import PlantEntry


class TreatmentController:
    def __init__(self, db: Database, catalog: list[PlantEntry]):
        self.db = db
        self._lock = threading.Lock()
        self.choices = deficiency_choices(catalog)
        self.allowed = {item["id"]: item["label"] for item in self.choices}
        self.last: dict | None = None
        self.db.close_open_treatments(utc_iso(), "startup_safe_state")

    def confirm(self, report: dict, treatment_id: str) -> dict:
        with self._lock:
            if report is None or report.get("report_id") is None:
                raise SafetyError("Check a photo before adding to irrigation.")
            label = self.allowed.get(treatment_id)
            if label is None:
                raise SafetyError("Choose a deficiency from the list.")
            moment = utc_now()
            stamp = utc_iso(moment)
            event_id = self.db.open_treatment(treatment_id, report.get("report_id"), stamp, 0, "simulated")
            self.db.close_treatment(event_id, stamp, "recorded", 0)
            self.last = {"treatment_id": treatment_id, "label": label}
            return self._public_unlocked()

    def public(self) -> dict:
        with self._lock:
            return self._public_unlocked()

    def _public_unlocked(self) -> dict:
        if self.last is None:
            return {
                "active": False,
                "treatment_id": None,
                "label": None,
                "note": "Nothing is recorded. This page does not open a valve.",
                "choices": self.choices,
            }
        return {
            "active": False,
            "treatment_id": self.last["treatment_id"],
            "label": self.last["label"],
            "note": f"{self.last['label']} recorded on this computer. This page does not open a valve or talk to the Arduino Uno.",
            "choices": self.choices,
        }


def deficiency_choices(catalog: list[PlantEntry]) -> list[dict]:
    choices = []
    for entry in catalog:
        if entry.kind not in ("deficiency", "disease"):
            continue
        choice_id = entry.treatment_id or entry.id
        choices.append({"id": choice_id, "label": choice_label(entry.id)})
    return choices


def choice_label(entry_id: str) -> str:
    if entry_id == "multiple":
        return "Mixed"
    word = str(entry_id or "")
    return word[:1].upper() + word[1:]
