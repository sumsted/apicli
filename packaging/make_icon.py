"""Generate packaging/icons/apicli_1024.png without third-party libraries.

Draws a rounded dark tile with a neon-cyan chevron prompt and a magenta
underscore, matching the app's cyberpunk palette. Pure stdlib so it works
anywhere; the macOS build script turns the PNG into an .icns with sips/iconutil.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

SIZE = 1024
RADIUS = 224
BG = (0x0B, 0x0F, 0x1A)
CYAN = (0x00, 0xE5, 0xFF)
MAGENTA = (0xFF, 0x2E, 0x97)

# Chevron ("greater-than") strokes and the underscore bar.
SEGMENTS = [((320.0, 300.0), (575.0, 512.0)), ((575.0, 512.0), (320.0, 724.0))]
STROKE_HALF = 34.0
BAR = (610.0, 690.0, 840.0, 726.0)


def _round_rect_sdf(x: float, y: float) -> float:
    half = SIZE / 2
    dx = abs(x - half) - (half - RADIUS)
    dy = abs(y - half) - (half - RADIUS)
    return math.hypot(max(dx, 0.0), max(dy, 0.0)) + min(max(dx, dy), 0.0) - RADIUS


def _dist_to_segment(px, py, a, b) -> float:
    (ax, ay), (bx, by) = a, b
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    c1 = vx * wx + vy * wy
    if c1 <= 0:
        return math.hypot(px - ax, py - ay)
    c2 = vx * vx + vy * vy
    if c2 <= c1:
        return math.hypot(px - bx, py - by)
    t = c1 / c2
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def _blend(base, overlay, alpha):
    return tuple(int(round(b * (1 - alpha) + o * alpha)) for b, o in zip(base, overlay))


def _pixel(x: float, y: float) -> tuple[int, int, int, int]:
    d = _round_rect_sdf(x, y)
    coverage = min(1.0, max(0.0, 0.5 - d))
    if coverage <= 0:
        return (0, 0, 0, 0)

    color = BG
    if -16.0 <= d <= 0.0:
        color = _blend(color, CYAN, (1.0 - abs(d) / 16.0) * 0.55)

    if 250.0 <= x <= 640.0 and 250.0 <= y <= 780.0:
        dc = min(_dist_to_segment(x, y, *seg) for seg in SEGMENTS)
        if dc <= STROKE_HALF:
            color = CYAN

    x0, y0, x1, y1 = BAR
    if x0 <= x <= x1 and y0 <= y <= y1:
        color = MAGENTA

    return (*color, int(round(coverage * 255)))


def _write_png(path: Path, size: int) -> None:
    raw = bytearray()
    for row in range(size):
        raw.append(0)  # filter: none
        y = row + 0.5
        for col in range(size):
            raw.extend(_pixel(col + 0.5, y))

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def main() -> None:
    out = Path(__file__).with_name("icons") / "apicli_1024.png"
    _write_png(out, SIZE)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
