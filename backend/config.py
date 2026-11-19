"""Runtime configuration.

This computer stands in for the Raspberry Pi while the lab is closed.
The same paths work on Windows, macOS, and Linux, and can move to the Pi later.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Config:
    root: Path
    db_path: Path
    field_path: Path
    plant_database_path: Path
    inspection_path: Path
    host: str
    port: int
    tick_wall_seconds: float


def load_config() -> Config:
    root = ROOT
    return Config(
        root=root,
        db_path=Path(os.environ.get("KSHETRA_DB", root / "data" / "kshetra.db")),
        field_path=Path(os.environ.get("KSHETRA_FIELD", root / "data" / "field.json")),
        plant_database_path=Path(os.environ.get("KSHETRA_PLANT_DB", root / "plant_database")),
        inspection_path=Path(os.environ.get("KSHETRA_INSPECTIONS", root / "data" / "inspections")),
        host=os.environ.get("KSHETRA_HOST", "127.0.0.1"),
        port=int(os.environ.get("KSHETRA_PORT", "5000")),
        tick_wall_seconds=float(os.environ.get("KSHETRA_TICK_SECONDS", "1.0")),
    )
