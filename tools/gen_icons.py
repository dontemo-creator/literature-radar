#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build-time only: render the radar mark to the PNG sizes a PWA needs.

Requires Pillow, which is NOT a runtime dependency -- the icons are generated
once and shipped as files, so the app itself stays standard-library only.

    python3 tools/gen_icons.py
"""
from __future__ import annotations

import math
import pathlib
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("This build tool needs Pillow:  python3 -m pip install pillow")

OUT = pathlib.Path(__file__).resolve().parent.parent / "app" / "web" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

SS = 4                     # supersampling factor
BASE = 512
TOP = (77, 138, 218)       # #4d8ada
BOTTOM = (40, 81, 143)     # #28518f
BLIP = (255, 206, 138)     # #ffce8a


def _gradient(size: int) -> Image.Image:
    """Diagonal top-left -> bottom-right gradient."""
    small = Image.new("RGB", (size, size))
    px = small.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
    return small


def _rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def render(size: int, *, radius_pct: float = 0.22, inset_pct: float = 0.0,
           square: bool = False) -> Image.Image:
    """Render the mark.  ``inset_pct`` leaves a safe margin for maskable icons."""
    S = size * SS
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    inset = round(S * inset_pct)
    tile = S - 2 * inset
    grad = _gradient(64).resize((tile, tile), Image.LANCZOS).convert("RGBA")
    if not square:
        grad.putalpha(_rounded_mask(tile, round(tile * radius_pct)))
    canvas.paste(grad, (inset, inset), grad)

    art = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    u = tile / 34.0                       # the SVG was authored on a 34-unit grid
    ox, oy = inset + 8.5 * u, inset + 24.5 * u      # radar origin
    bx, by = inset + 24.0 * u, inset + 9.5 * u      # blip

    def arc(radius_u: float, alpha: int, width_u: float = 1.7):
        r = radius_u * u
        box = [ox - r, oy - r, ox + r, oy + r]
        d.arc(box, start=270, end=360, fill=(255, 255, 255, alpha),
              width=max(1, round(width_u * u)))

    arc(10, 128)
    arc(16, 66)

    # dashed sweep line from origin toward the blip
    steps = 9
    for i in range(steps):
        if i % 2:
            continue
        t0, t1 = i / steps, (i + 0.62) / steps
        d.line([ox + (bx - ox) * t0, oy + (by - oy) * t0,
                ox + (bx - ox) * t1, oy + (by - oy) * t1],
               fill=(255, 255, 255, 56), width=max(1, round(1.2 * u)))

    def dot(cx, cy, r_u, colour):
        r = r_u * u
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour)

    dot(bx, by, 5.4, BLIP + (56,))        # halo
    dot(ox, oy, 2.4, (255, 255, 255, 255))
    dot(bx, by, 3.1, BLIP + (255,))

    canvas = Image.alpha_composite(canvas, art)
    return canvas.resize((size, size), Image.LANCZOS)


TARGETS = [
    ("icon-192.png", 192, {}),
    ("icon-256.png", 256, {}),
    ("icon-384.png", 384, {}),
    ("icon-512.png", 512, {}),
    ("apple-touch-icon.png", 180, {"radius_pct": 0.0, "square": True}),
    ("maskable-192.png", 192, {"radius_pct": 0.0, "square": True, "inset_pct": 0.0}),
    ("maskable-512.png", 512, {"radius_pct": 0.0, "square": True, "inset_pct": 0.0}),
    ("favicon-32.png", 32, {}),
    ("favicon-16.png", 16, {}),
]

if __name__ == "__main__":
    for name, size, kw in TARGETS:
        # Maskable icons must survive a circular crop, so keep the art inside 80%.
        if name.startswith("maskable"):
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            grad = _gradient(64).resize((size, size), Image.LANCZOS).convert("RGBA")
            img.paste(grad, (0, 0))
            art = render(round(size * 0.72), radius_pct=0.0, square=True)
            off = (size - art.width) // 2
            # re-render art transparent-backed by compositing only the strokes
            inner = render(round(size * 0.72))
            img.paste(inner, (off, off), inner)
            img.save(OUT / name)
        else:
            render(size, **kw).save(OUT / name)
        print("  wrote", name, "%dx%d" % (size, size))
    print("\nicons in", OUT)
