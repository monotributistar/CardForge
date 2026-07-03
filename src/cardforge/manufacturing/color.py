"""Colour helpers for manufacturing checks (QR/inlay contrast).

Contrast is judged with the WCAG relative-luminance ratio (1:1 identical …
21:1 black-on-white). A QR scans when its modules and the surrounding surface
differ enough in luminance; the camera doesn't care which is darker.
"""

from __future__ import annotations

from typing import Tuple


def _parse_hex(color: str) -> Tuple[int, int, int]:
    c = color.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return (128, 128, 128)
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def relative_luminance(color: str) -> float:
    """WCAG relative luminance in [0, 1]."""
    def lin(v: int) -> float:
        s = v / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = _parse_hex(color)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two hex colours (1.0 … 21.0)."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)
