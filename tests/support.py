"""Shared test setup."""

from __future__ import annotations

from pathlib import Path

from backend.app import create_app
from backend.config import Config

ROOT = Path(__file__).resolve().parents[1]


def make_config(directory: Path) -> Config:
    return Config(
        root=ROOT,
        db_path=directory / "test.db",
        field_path=ROOT / "data" / "field.json",
        plant_database_path=ROOT / "plant_database",
        inspection_path=directory / "inspections",
        host="127.0.0.1",
        port=5000,
        tick_wall_seconds=1.0,
    )


def make_app(directory: Path):
    return create_app(make_config(directory))
