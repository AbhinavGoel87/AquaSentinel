"""Timed treatment into the irrigation water.

A treatment starts only after the farmer confirms a deficiency or disease match.
It stops at its time limit, on emergency stop, and when the program starts.
"""

from __future__ import annotations

import threading

from backend.database.db import Database
from backend.irrigation.safety import SafetyError
from backend.utils.timeutil import utc_iso, utc_now
from backend.vision.catalog import MAX_DOSE_SECONDS


class TreatmentController:
    def __init__(self, db: Database):
        self.db = db
        self._lock = threading.Lock()
        self.active: dict | None = None
        self.db.close_open_treatments(utc_iso(), "startup_safe_state")

    def confirm(self, report: dict) -> dict:
        with self._lock:
            if self.active is not None:
                raise SafetyError("A timer for the last photo is already running.")
            if not report.get("can_treat"):
                raise SafetyError("This photo is not clear enough to add a treatment.")
            if report.get("kind") not in ("deficiency", "disease"):
                raise SafetyError("Only a deficiency or disease match can be recorded.")
            treatment_id = report.get("treatment_id")
            if not treatment_id:
                raise SafetyError("This result has no treatment.")
            dose = report.get("dose_seconds") or 30
            dose = max(5, min(int(dose), MAX_DOSE_SECONDS))
            started = utc_now()
            event_id = self.db.open_treatment(
                treatment_id,
                report.get("report_id"),
                utc_iso(started),
                dose,
                "simulated",
            )
            self.active = {
                "event_id": event_id,
                "treatment_id": treatment_id,
                "report_id": report.get("report_id"),
                "started": started,
                "max_seconds": dose,
                "title": report.get("title"),
            }
            return self._public_unlocked()

    def halt(self, reason: str) -> dict:
        with self._lock:
            self._stop_unlocked(reason)
            return self._public_unlocked()

    def tick(self, moment, emergency: bool) -> None:
        with self._lock:
            if self.active is None:
                return
            if emergency:
                self._stop_unlocked("emergency_stop", moment)
                return
            elapsed = (moment - self.active["started"]).total_seconds()
            if elapsed >= self.active["max_seconds"]:
                self._stop_unlocked("max_duration", moment)

    def public(self) -> dict:
        with self._lock:
            return self._public_unlocked()

    def _stop_unlocked(self, reason: str, moment=None) -> None:
        if self.active is None:
            return
        moment = moment or utc_now()
        elapsed = round(max(0.0, (moment - self.active["started"]).total_seconds()), 1)
        self.db.close_treatment(self.active["event_id"], utc_iso(moment), reason, elapsed)
        self.active = None

    def _public_unlocked(self) -> dict:
        if self.active is None:
            return {
                "active": False,
                "treatment_id": None,
                "seconds_remaining": 0,
                "note": "Nothing is recorded. This page does not open a valve.",
            }
        elapsed = (utc_now() - self.active["started"]).total_seconds()
        remaining = max(0, int(self.active["max_seconds"] - elapsed))
        return {
            "active": True,
            "treatment_id": self.active["treatment_id"],
            "seconds_remaining": remaining,
            "title": self.active["title"],
            "note": "Timer recorded on this computer. It does not open a valve or talk to the Arduino Uno.",
        }
