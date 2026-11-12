"""Match one rover photo to the uploaded plant database.

The score is how close the new photo's colors are to the example photos.
It is not a measured accuracy and it is not a soil test.
"""

from __future__ import annotations

from backend.vision.catalog import PlantEntry
from backend.vision.features import feature_distance

ACCEPT_SCORE = 0.62
CLEAR_MARGIN = 0.08


def advise(photo_features: dict, entries: list[PlantEntry]) -> dict:
    if _poor_photo(photo_features):
        return _uncertain(
            "The photo is too dark, too bright, or too small to compare with the database.",
            0.0,
        )
    scored = []
    for entry in entries:
        if not entry.examples:
            continue
        distance = min(feature_distance(photo_features, example.features) for example in entry.examples)
        scored.append((1 / (1 + distance), entry))
    if not scored:
        return _uncertain("The plant database has no example photos yet. Add pictures under each entry.", 0.0)
    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    if best_score < ACCEPT_SCORE:
        return {
            "entry_id": "discrepancy",
            "kind": "discrepancy",
            "title": "The plant looks different",
            "farmer_message": (
                "This photo does not match the healthy examples, and it does not clearly match "
                "one deficiency or disease in the database."
            ),
            "recommended_action": "Look at the plant in person before adding anything to the irrigation water.",
            "treatment_id": None,
            "dose_seconds": None,
            "match_score": round(best_score, 3),
            "method": "database-color-match",
            "can_treat": False,
        }
    if best.kind != "healthy" and best_score - second_score < CLEAR_MARGIN:
        return _uncertain(
            "Two database entries are too close. Look at the plant before choosing a treatment.",
            best_score,
        )
    return {
        "entry_id": best.id,
        "kind": best.kind,
        "title": best.title,
        "farmer_message": best.farmer_message,
        "recommended_action": best.recommended_action,
        "treatment_id": best.treatment_id if best.kind in ("deficiency", "disease") else None,
        "dose_seconds": best.dose_seconds if best.kind in ("deficiency", "disease") else None,
        "match_score": round(best_score, 3),
        "method": "database-color-match",
        "can_treat": best.kind in ("deficiency", "disease") and bool(best.treatment_id),
    }


def _poor_photo(features: dict) -> bool:
    brightness = features.get("brightness", 0)
    count = features.get("pixel_count", 0)
    return count < 16 or brightness < 20 or brightness > 245


def _uncertain(message: str, score: float) -> dict:
    return {
        "entry_id": "uncertain",
        "kind": "uncertain",
        "title": "Not enough to decide",
        "farmer_message": message,
        "recommended_action": "Take another photo in daylight. Do not add a treatment from this picture.",
        "treatment_id": None,
        "dose_seconds": None,
        "match_score": round(score, 3),
        "method": "database-color-match",
        "can_treat": False,
    }
