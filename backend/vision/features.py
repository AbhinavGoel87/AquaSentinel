"""Turn a plant photo into a few plain numbers.

These numbers are color shares. They are not a nutrient measurement.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image


def features_from_bytes(payload: bytes) -> dict:
    image = Image.open(BytesIO(payload)).convert("RGB")
    image.thumbnail((80, 80))
    raw = image.tobytes()
    pixels = list(zip(raw[0::3], raw[1::3], raw[2::3]))
    if not pixels:
        return _empty()
    green = yellow = brown = 0
    brightness = 0.0
    for red, gre, blue in pixels:
        brightness += (red + gre + blue) / 3
        if gre > red + 15 and gre > blue + 15 and gre > 60:
            green += 1
        elif red > 140 and gre > 120 and blue < 110:
            yellow += 1
        elif red > 90 and gre < 80 and blue < 70:
            brown += 1
    count = len(pixels)
    return {
        "green_ratio": green / count,
        "yellow_ratio": yellow / count,
        "brown_ratio": brown / count,
        "brightness": brightness / count,
        "pixel_count": count,
    }


def _empty() -> dict:
    return {
        "green_ratio": 0.0,
        "yellow_ratio": 0.0,
        "brown_ratio": 0.0,
        "brightness": 0.0,
        "pixel_count": 0,
    }


def feature_distance(left: dict, right: dict) -> float:
    keys = ("green_ratio", "yellow_ratio", "brown_ratio")
    brightness_gap = abs(left["brightness"] - right["brightness"]) / 255
    color = sum((left[key] - right[key]) ** 2 for key in keys) ** 0.5
    return color + 0.25 * brightness_gap
