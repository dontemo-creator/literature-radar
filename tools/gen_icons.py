#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the monochrome book mark used only for PWA and browser icons.

The visible site uses a text wordmark. Pillow is a build-time dependency only.
"""
from __future__ import annotations

from pathlib import Path
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("This build tool needs Pillow: python3 -m pip install pillow")

OUT = Path(__file__).resolve().parent.parent / "app" / "web" / "icons"
OUT.mkdir(parents=True, exist_ok=True)
SCALE = 8


def render(size: int, maskable: bool = False) -> Image.Image:
    big = size * SCALE
    image = Image.new("RGB", (big, big), "white")
    draw = ImageDraw.Draw(image)
    # Both pages share a spine. The broad, open silhouette reads at 16 px.
    margin = 0.21 if maskable else 0.14
    left = round(big * margin)
    right = big - left
    top = round(big * 0.24)
    bottom = round(big * 0.73)
    middle = big // 2
    stroke = max(SCALE, round(big * (0.052 if size <= 32 else 0.041)))
    ink = (17, 17, 17)
    draw.line([(left, top), (left, bottom), (middle, bottom + big * .065),
               (middle, top + big * .065), (left, top)],
              fill=ink, width=stroke, joint="curve")
    draw.line([(middle, top + big * .065), (right, top), (right, bottom),
               (middle, bottom + big * .065)],
              fill=ink, width=stroke, joint="curve")
    draw.line([(middle, top + big * .065), (middle, bottom + big * .065)],
              fill=ink, width=stroke)
    return image.resize((size, size), Image.Resampling.LANCZOS)


TARGETS = [
    ("icon-192.png", 192, False),
    ("icon-256.png", 256, False),
    ("icon-384.png", 384, False),
    ("icon-512.png", 512, False),
    ("apple-touch-icon.png", 180, False),
    ("maskable-192.png", 192, True),
    ("maskable-512.png", 512, True),
    ("favicon-32.png", 32, False),
    ("favicon-16.png", 16, False),
]

if __name__ == "__main__":
    for name, size, maskable in TARGETS:
        render(size, maskable).save(OUT / name)
        print("wrote", name, f"{size}x{size}")
