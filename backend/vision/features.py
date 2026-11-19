"""Turn a plant photo into a few plain numbers.

The white paper around a leaf is ignored. The numbers describe the leaf
colors. They are not a nutrient measurement.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image

FEATURE_VERSION = 2


def features_from_bytes(payload: bytes) -> dict:
    image = Image.open(BytesIO(payload)).convert("RGB")
    image.thumbnail((128, 128))
    width, _height = image.size
    raw = image.tobytes()
    pixels = list(zip(raw[0::3], raw[1::3], raw[2::3]))
    brightness = 0.0
    leaf_index = []
    for index, (red, gre, blue) in enumerate(pixels):
        brightness += (red + gre + blue) / 3
        brightest = max(red, gre, blue)
        darkest = min(red, gre, blue)
        if darkest > 205 and brightest - darkest < 36:
            continue
        if brightest < 28:
            continue
        leaf_index.append(index)
    if len(leaf_index) < 24:
        return _empty(brightness / len(pixels) if pixels else 0.0)
    hue_hist = [0] * 12
    deep = pale = 0
    cols = [index % width for index in leaf_index]
    rows = [index // width for index in leaf_index]
    min_x, max_x = min(cols), max(cols)
    min_y, max_y = min(rows), max(rows)
    box_w = max(1, max_x - min_x)
    box_h = max(1, max_y - min_y)
    center_pale = center_count = margin_pale = margin_count = 0
    for index in leaf_index:
        red, gre, blue = pixels[index]
        hue_hist[min(11, int(_hue(red, gre, blue) * 12))] += 1
        is_pale = gre > 50 and red > 50 and abs(gre - red) <= 30 and (gre - blue) > 10
        is_deep = gre > red + 35 and gre > blue + 25 and 40 < gre < 170
        deep += int(is_deep)
        pale += int(is_pale)
        x = index % width
        y = index // width
        in_center = (min_x + box_w * 0.28) <= x <= (max_x - box_w * 0.28) and (
            min_y + box_h * 0.28
        ) <= y <= (max_y - box_h * 0.28)
        if in_center:
            center_count += 1
            center_pale += int(is_pale)
        else:
            margin_count += 1
            margin_pale += int(is_pale)
    count = len(leaf_index)
    vec = [
        deep / count,
        pale / count,
        (center_pale / center_count) if center_count else 0.0,
        (margin_pale / margin_count) if margin_count else 0.0,
    ]
    vec.extend(value / count for value in hue_hist)
    return {
        "brightness": brightness / len(pixels),
        "pixel_count": count,
        "pale": pale / count,
        "vec": vec,
    }


def _empty(brightness: float) -> dict:
    return {
        "brightness": brightness,
        "pixel_count": 0,
        "pale": 0.0,
        "vec": [0.0] * 16,
    }


def _hue(red: int, gre: int, blue: int) -> float:
    red_f, gre_f, blue_f = red / 255, gre / 255, blue / 255
    brightest = max(red_f, gre_f, blue_f)
    darkest = min(red_f, gre_f, blue_f)
    span = brightest - darkest
    if span == 0:
        return 0.0
    if brightest == red_f:
        hue = ((gre_f - blue_f) / span) % 6
    elif brightest == gre_f:
        hue = (blue_f - red_f) / span + 2
    else:
        hue = (red_f - gre_f) / span + 4
    return hue / 6


def feature_distance(left: dict, right: dict) -> float:
    return vec_distance(left.get("vec") or [], right.get("vec") or [])


def vec_distance(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 10.0
    total = 0.0
    for index, (left_value, right_value) in enumerate(zip(left, right)):
        weight = 1.6 if index < 4 else 1.0
        total += weight * (left_value - right_value) ** 2
    return total ** 0.5
