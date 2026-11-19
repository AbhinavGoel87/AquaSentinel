"""SQLite storage for readings, valve events, and alerts."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from backend.utils.timeutil import utc_iso

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 3000")
            self._conn = conn
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def ensure_schema(self) -> None:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with self._lock:
            conn = self.connect()
            conn.executescript(schema)
            conn.commit()

    def initialize(self, field: dict) -> None:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with self._lock:
            conn = self.connect()
            conn.executescript(schema)
            self._upsert_field(conn, field)
            self._startup_safe_state(conn)
            conn.commit()

    def latest_raw(self) -> dict[str, float]:
        with self._lock:
            rows = self.connect().execute(
                """
                SELECT s.id AS sensor_id, r.raw_percent
                FROM sensors s
                JOIN sensor_readings r ON r.id = (
                    SELECT id FROM sensor_readings
                    WHERE sensor_id = s.id AND raw_percent IS NOT NULL
                    ORDER BY id DESC LIMIT 1
                )
                """
            ).fetchall()
        return {row["sensor_id"]: float(row["raw_percent"]) for row in rows}

    def insert_readings(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock:
            conn = self.connect()
            conn.executemany(
                """
                INSERT INTO sensor_readings (
                    sensor_id, raw_percent, moisture_percent, quality,
                    source, recorded_at, sim_time
                ) VALUES (
                    :sensor_id, :raw_percent, :moisture_percent, :quality,
                    :source, :recorded_at, :sim_time
                )
                """,
                rows,
            )
            conn.commit()

    def open_irrigation(
        self,
        zone_id: str,
        mode: str,
        reason: str,
        started_at: str,
        source: str,
    ) -> int:
        with self._lock:
            conn = self.connect()
            cursor = conn.execute(
                """
                INSERT INTO irrigation_events (zone_id, mode, reason, started_at, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (zone_id, mode, reason, started_at, source),
            )
            conn.execute("UPDATE zones SET valve_open = 1 WHERE id = ?", (zone_id,))
            conn.commit()
            return int(cursor.lastrowid)

    def close_irrigation(
        self,
        zone_id: str,
        ended_at: str,
        stop_reason: str,
        duration_sec: float,
    ) -> None:
        with self._lock:
            conn = self.connect()
            conn.execute(
                """
                UPDATE irrigation_events
                SET ended_at = ?, stop_reason = ?, duration_sec = ?, estimated_liters = NULL
                WHERE zone_id = ? AND ended_at IS NULL
                """,
                (ended_at, stop_reason, duration_sec, zone_id),
            )
            conn.execute("UPDATE zones SET valve_open = 0 WHERE id = ?", (zone_id,))
            conn.commit()

    def raise_alert(self, severity: str, code: str, message: str, source: str) -> None:
        with self._lock:
            conn = self.connect()
            existing = conn.execute(
                """
                SELECT id FROM alerts
                WHERE code = ? AND acknowledged_at IS NULL
                LIMIT 1
                """,
                (code,),
            ).fetchone()
            if existing:
                return
            conn.execute(
                """
                INSERT INTO alerts (severity, code, message, source, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (severity, code, message, source, utc_iso()),
            )
            conn.commit()

    def acknowledge_code(self, code: str, when: str) -> None:
        with self._lock:
            conn = self.connect()
            conn.execute(
                """
                UPDATE alerts
                SET acknowledged_at = ?
                WHERE code = ? AND acknowledged_at IS NULL
                """,
                (when, code),
            )
            conn.commit()

    def recent_alerts(self, limit: int = 8) -> list[dict]:
        with self._lock:
            rows = self.connect().execute(
                """
                SELECT id, severity, code, message, source, created_at
                FROM alerts
                WHERE acknowledged_at IS NULL
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_events(self, limit: int = 20) -> list[dict]:
        with self._lock:
            rows = self.connect().execute(
                """
                SELECT id, zone_id, mode, reason, started_at, ended_at,
                       stop_reason, duration_sec, estimated_liters, source
                FROM irrigation_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def insert_inspection(self, rover_id: str, checkpoint_id: str | None, image_path: str, created_at: str, source: str) -> int:
        with self._lock:
            cursor = self.connect().execute(
                """
                INSERT INTO inspections (rover_id, checkpoint_id, image_path, created_at, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (rover_id, checkpoint_id, image_path, created_at, source),
            )
            self.connect().commit()
            return int(cursor.lastrowid)

    def insert_report(self, inspection_id: int, advice: dict, created_at: str) -> int:
        with self._lock:
            cursor = self.connect().execute(
                """
                INSERT INTO plant_reports (
                    inspection_id, entry_id, kind, title, farmer_message,
                    recommended_action, treatment_id, dose_seconds, match_score, method, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inspection_id,
                    advice["entry_id"],
                    advice["kind"],
                    advice["title"],
                    advice["farmer_message"],
                    advice["recommended_action"],
                    advice["treatment_id"],
                    advice["dose_seconds"],
                    advice["match_score"],
                    advice["method"],
                    created_at,
                ),
            )
            self.connect().commit()
            return int(cursor.lastrowid)

    def inspection_path(self, inspection_id: int) -> str | None:
        with self._lock:
            row = self.connect().execute(
                "SELECT image_path FROM inspections WHERE id = ?",
                (inspection_id,),
            ).fetchone()
        if row is None:
            return None
        return row["image_path"]

    def latest_report(self) -> dict | None:
        with self._lock:
            row = self.connect().execute(
                """
                SELECT r.id AS report_id, r.inspection_id, r.entry_id, r.kind, r.title,
                       r.farmer_message, r.recommended_action, r.treatment_id, r.dose_seconds,
                       r.match_score, r.method, r.created_at, i.image_path, i.rover_id, i.checkpoint_id
                FROM plant_reports r
                JOIN inspections i ON i.id = r.inspection_id
                ORDER BY r.id DESC
                LIMIT 1
                """
            ).fetchone()
        return dict(row) if row else None

    def open_treatment(self, treatment_id: str, report_id: int | None, started_at: str, max_seconds: int, source: str) -> int:
        with self._lock:
            cursor = self.connect().execute(
                """
                INSERT INTO treatment_events (
                    treatment_id, report_id, started_at, max_seconds, farmer_confirmed, source
                ) VALUES (?, ?, ?, ?, 1, ?)
                """,
                (treatment_id, report_id, started_at, max_seconds, source),
            )
            self.connect().commit()
            return int(cursor.lastrowid)

    def close_treatment(self, event_id: int, ended_at: str, stop_reason: str, duration_sec: float) -> None:
        with self._lock:
            conn = self.connect()
            conn.execute(
                """
                UPDATE treatment_events
                SET ended_at = ?, stop_reason = ?, duration_sec = ?
                WHERE id = ?
                """,
                (ended_at, stop_reason, duration_sec, event_id),
            )
            conn.commit()

    def close_open_treatments(self, ended_at: str, stop_reason: str) -> None:
        with self._lock:
            conn = self.connect()
            rows = conn.execute(
                "SELECT id, started_at FROM treatment_events WHERE ended_at IS NULL"
            ).fetchall()
            for row in rows:
                started = _parse_time(row["started_at"])
                current = _parse_time(ended_at)
                duration = round(max(0.0, (current - started).total_seconds()), 1)
                conn.execute(
                    """
                    UPDATE treatment_events
                    SET ended_at = ?, stop_reason = ?, duration_sec = ?
                    WHERE id = ?
                    """,
                    (ended_at, stop_reason, duration, row["id"]),
                )
            conn.commit()

    def _upsert_field(self, conn: sqlite3.Connection, field: dict) -> None:
        for zone in field["zones"]:
            conn.execute(
                """
                INSERT INTO zones (
                    id, name, crop_label, low_threshold, target_moisture,
                    max_duration_sec, cooldown_sec, mode, valve_open
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', 0)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    crop_label = excluded.crop_label,
                    low_threshold = excluded.low_threshold,
                    target_moisture = excluded.target_moisture,
                    max_duration_sec = excluded.max_duration_sec,
                    cooldown_sec = excluded.cooldown_sec
                """,
                (
                    zone["id"],
                    zone["name"],
                    zone["crop_label"],
                    zone["low_threshold"],
                    zone["target_moisture"],
                    zone["max_duration_sec"],
                    zone["cooldown_sec"],
                ),
            )
        for sensor in field["sensors"]:
            conn.execute(
                """
                INSERT INTO sensors (
                    id, zone_id, label, pos_x, pos_y,
                    calibration_offset, calibration_scale, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                    zone_id = excluded.zone_id,
                    label = excluded.label,
                    pos_x = excluded.pos_x,
                    pos_y = excluded.pos_y,
                    calibration_offset = excluded.calibration_offset,
                    calibration_scale = excluded.calibration_scale
                """,
                (
                    sensor["id"],
                    sensor["zone_id"],
                    sensor["label"],
                    sensor["x"],
                    sensor["y"],
                    sensor["calibration_offset"],
                    sensor["calibration_scale"],
                ),
            )

    def _startup_safe_state(self, conn: sqlite3.Connection) -> None:
        now = utc_iso()
        open_rows = conn.execute(
            """
            SELECT id, started_at FROM irrigation_events WHERE ended_at IS NULL
            """
        ).fetchall()
        for row in open_rows:
            started = _parse_time(row["started_at"])
            current = _parse_time(now)
            duration = round(max(0.0, (current - started).total_seconds()), 1)
            conn.execute(
                """
                UPDATE irrigation_events
                SET ended_at = ?, stop_reason = 'startup_safe_state', duration_sec = ?
                WHERE id = ?
                """,
                (now, duration, row["id"]),
            )
        conn.execute("UPDATE zones SET valve_open = 0")


def _parse_time(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))
