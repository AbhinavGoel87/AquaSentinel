"""Decide which soil readings are allowed to describe a zone.

A single odd sensor is reported and then left out of the average when the
other sensors in that zone agree with each other. Fewer than two usable
readings means the zone cannot support an automatic watering decision.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

REASON_OK = "Usable reading."
REASON_MISSING = "No reading from this sensor."
REASON_INVALID = "Reading is outside 0–100 and was rejected."
REASON_SUSPECT = "Too far from the other sensors in this zone, so it was left out of the average."


@dataclass(frozen=True)
class SensorJudgement:
    sensor_id: str
    moisture: float | None
    quality: str
    reason: str


@dataclass(frozen=True)
class ZoneJudgement:
    average: float | None
    included_count: int
    status: str
    uneven: bool
    summary: str
    sensors: list[SensorJudgement]


def judge_zone(
    samples: list[tuple[str, float | None]],
    *,
    min_sensors: int,
    suspect_gap: float,
    neighbor_agreement: float,
    uneven_spread: float,
) -> ZoneJudgement:
    by_id: dict[str, SensorJudgement] = {}
    valid: list[tuple[str, float]] = []

    for sensor_id, value in samples:
        if value is None:
            by_id[sensor_id] = SensorJudgement(sensor_id, None, "missing", REASON_MISSING)
            continue
        if not math.isfinite(value) or value < 0 or value > 100:
            shown = float(value) if math.isfinite(value) else None
            by_id[sensor_id] = SensorJudgement(sensor_id, shown, "invalid", REASON_INVALID)
            continue
        by_id[sensor_id] = SensorJudgement(sensor_id, float(value), "ok", REASON_OK)
        valid.append((sensor_id, float(value)))

    if len(valid) >= 3:
        median = statistics.median(value for _, value in valid)
        for sensor_id, value in valid:
            others = [other for other_id, other in valid if other_id != sensor_id]
            neighbors_agree = max(others) - min(others) <= neighbor_agreement
            if abs(value - median) > suspect_gap and neighbors_agree:
                by_id[sensor_id] = SensorJudgement(sensor_id, value, "suspect", REASON_SUSPECT)

    ordered = [by_id[sensor_id] for sensor_id, _ in samples]
    included = [item.moisture for item in ordered if item.quality == "ok" and item.moisture is not None]
    spread = (max(included) - min(included)) if len(included) >= 2 else 0.0

    if len(included) < min_sensors:
        average = None
        status = "insufficient"
        summary = "Not enough usable sensors to judge this zone."
    elif spread > uneven_spread:
        average = round(sum(included) / len(included), 1)
        status = "uneven"
        summary = "Sensors disagree across the bed. Look before irrigating."
    else:
        average = round(sum(included) / len(included), 1)
        status = "ok"
        summary = "Enough sensors agree to describe this zone."

    return ZoneJudgement(
        average=average,
        included_count=len(included),
        status=status,
        uneven=status == "uneven",
        summary=summary,
        sensors=ordered,
    )
