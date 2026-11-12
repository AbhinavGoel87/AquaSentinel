"""Pure moisture step used by the simulator.

Rates are scenario settings from data/field.json. They are not a soil-physics model.
"""

from __future__ import annotations

import random


def advance_moisture(
    current: float,
    *,
    valve_open: bool,
    dt_hours: float,
    dry_rate: float,
    irrigate_rate: float,
    noise: float,
    rng: random.Random,
) -> float:
    delta = -dry_rate * dt_hours
    if valve_open:
        delta += irrigate_rate * dt_hours
    if noise:
        delta += rng.uniform(-noise, noise)
    return min(100.0, max(0.0, current + delta))


def apply_calibration(raw: float | None, scale: float, offset: float) -> float | None:
    if raw is None:
        return None
    return raw * scale + offset
