"""Base body region — the 2D footprint of the card body, before extrusion.

Solid:   the whole outline.
Lattice: a solid rim of `border` mm around the perimeter, filled with a
         pattern (dots/lines/grid/hex). Everything clipped to the outline, so
         the card edge stays clean while the interior is an open grid.

A lattice base is why features may need a backing pad: geometry sitting over
the open grid would otherwise float (see kernel/compile.py).
"""

from __future__ import annotations

from manifold3d import CrossSection

from cardforge.document.schema_v2 import DocumentV2
from cardforge.kernel import patterns as pat
from cardforge.kernel.features import outline_cross_section


def _rim(outline: CrossSection, border: float) -> CrossSection:
    """Solid perimeter band of `border` mm inside the outline."""
    if border <= 0:
        return CrossSection()
    inner = outline.offset(-border, 0)  # 0 = Round join; erodes the outline
    if inner.is_empty():
        return outline
    return outline - inner


def _lattice_pattern(outline: CrossSection, pattern: str, spacing: float,
                     line_width: float) -> CrossSection:
    if pattern == "dots":
        return pat.dots(outline, spacing, line_width * 1.5)
    if pattern == "lines":
        return pat.lines(outline, spacing, line_width, angle_deg=0.0)
    if pattern == "grid":
        return pat.grid(outline, spacing, line_width, angle_deg=0.0)
    if pattern == "hex":
        return pat.hex_grid(outline, spacing, line_width)
    raise ValueError(f"unknown lattice pattern: {pattern}")


def base_region(doc: DocumentV2) -> CrossSection:
    """The 2D region (physical space) to extrude into the card body."""
    outline = outline_cross_section(doc)
    fill = doc.object.fill
    if fill.type == "solid":
        return outline
    if fill.type == "lattice":
        rim = _rim(outline, fill.border)
        grid = _lattice_pattern(outline, fill.pattern, fill.spacing, fill.line_width)
        region = rim + grid
        return region if not region.is_empty() else outline
    raise ValueError(f"unknown fill type: {fill.type}")


def is_lattice(doc: DocumentV2) -> bool:
    return doc.object.fill.type == "lattice"
