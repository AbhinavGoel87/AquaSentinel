"""Tiny PNG writer so the plant database can ship example pictures."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def write_rgb_png(path: Path, width: int, height: int, paint) -> None:
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            red, green, blue = paint(x, y, width, height)
            row.extend((red & 255, green & 255, blue & 255))
        rows.append(b"\x00" + bytes(row))
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
