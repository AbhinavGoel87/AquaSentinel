"""Match one rover photo to the uploaded plant database.

The score is how close the new photo's colors are to the example photos.
It is not a measured accuracy and it is not a soil test.
"""

from __future__ import annotations

from backend.vision.catalog import PlantEntry
from backend.vision.features import vec_distance

ACCEPT_SCORE = 0.55
CLEAR_MARGIN = 0.04
NEAR_COPY = 0.02
# Healthy CoLeaf leaves stay under this share of yellow-green tissue.
PALE_HEALTHY_LIMIT = 0.10


def advise(photo_features: dict, entries: list[PlantEntry]) -> dict:
    if _poor_photo(photo_features):
        return _uncertain(
            "The photo is too dark, too bright, or too small to compare with the database.",
            0.0,
        )
    photo_vec = photo_features.get("vec") or []
    pale = photo_features.get("pale", 0.0)
    scored = []
    for entry in entries:
        distance = _entry_distance(photo_vec, pale, entry)
        if distance is None:
            continue
        scored.append((1 / (1 + distance), entry))
    if not scored:
        return _uncertain("The plant database has no example photos yet. Add pictures under each entry.", 0.0)
    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    if best_score - second_score < CLEAR_MARGIN:
        return _uncertain(
            "Two database entries are too close. Look at the plant before choosing a treatment.",
            best_score,
        )
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


def _entry_distance(photo_vec: list[float], pale: float, entry: PlantEntry) -> float | None:
    vectors = [example.features.get("vec") or [] for example in entry.examples]
    vectors = [vector for vector in vectors if len(vector) == len(photo_vec) and photo_vec]
    if not vectors:
        return None
    nearest = min(vec_distance(photo_vec, vector) for vector in vectors)
    # A yellowing leaf is outside the healthy examples, so it cannot win as healthy
    # just because one green photo is a near neighbor.
    if entry.kind == "healthy" and pale > PALE_HEALTHY_LIMIT and nearest > NEAR_COPY:
        return None
    if nearest <= NEAR_COPY:
        return nearest
    width = len(vectors[0])
    center = [sum(vector[index] for vector in vectors) / len(vectors) for index in range(width)]
    return vec_distance(photo_vec, center)


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
