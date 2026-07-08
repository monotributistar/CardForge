"""Surface patterns (tramas) — dot/line/grid/hex tilings and tile positions
for text-repeat, clipped to a region CrossSection.

All generators take the clip region in PHYSICAL space and return the pattern
already intersected with it, so callers place the region first and never
worry about pattern overflow.
"""

from __future__ import annotations

import math
from typing import Iterator, List, Tuple

from manifold3d import CrossSection, FillRule, OpType

from cardforge.kernel.shapes2d import circle

Point = Tuple[float, float]

# Hard ceiling on tile count — beyond this a pattern is unprintable anyway
# and the boolean union would stall the compile (or OOM).
MAX_TILES = 25_000


class PatternDensityError(ValueError):
    """Spacing gives a non-positive step or an absurd number of tiles."""


def _region_frame(region: CrossSection, angle_deg: float):
    """Iteration frame covering the region's bounds even when rotated."""
    min_x, min_y, max_x, max_y = region.bounds()
    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
    # Diagonal covers any rotation of the bounds
    diag = math.hypot(max_x - min_x, max_y - min_y)
    return cx, cy, diag


def tile_positions(region: CrossSection, spacing: float,
                   angle_deg: float = 0.0, stagger: bool = False,
                   spacing_y: float | None = None,
                   margin: float | None = None) -> Iterator[Point]:
    """Yield tile centers on a (possibly rotated, possibly staggered) grid
    covering `region`. Centers are pre-filtered to the region's bounds plus
    `margin` (default: one step) — the caller still clips real geometry.

    `spacing` steps along the row direction (horizontal at angle 0);
    `spacing_y` steps between rows and defaults to `spacing`.

    Raises PatternDensityError when a step is <= 0 or the grid would exceed
    MAX_TILES positions.
    """
    sy = spacing_y or spacing
    if min(spacing, sy) <= 0:
        raise PatternDensityError("pattern spacing must be > 0")
    min_x, min_y, max_x, max_y = region.bounds()
    m = margin if margin is not None else max(spacing, sy)
    # Area bound — independent of angle/stagger, so it can't undercount.
    est = (((max_x - min_x + 2 * m) / spacing + 1)
           * ((max_y - min_y + 2 * m) / sy + 1))
    if est > MAX_TILES:
        raise PatternDensityError(
            f"pattern needs ~{int(est):,} tiles (max {MAX_TILES:,}) — "
            "increase the spacing or shrink the region")
    cx, cy, diag = _region_frame(region, angle_deg)
    n = max(1, int(math.ceil(diag / min(spacing, sy))) + 1)
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)          # row direction
    vx, vy = -math.sin(a), math.cos(a)         # column direction
    lo_x, hi_x, lo_y, hi_y = min_x - m, max_x + m, min_y - m, max_y + m
    for j in range(-n, n + 1):
        row_offset = (spacing / 2 if (stagger and j % 2) else 0.0)
        for i in range(-n, n + 1):
            px = cx + (i * spacing + row_offset) * ux + j * sy * vx
            py = cy + (i * spacing + row_offset) * uy + j * sy * vy
            if lo_x <= px <= hi_x and lo_y <= py <= hi_y:
                yield (px, py)


def dots(region: CrossSection, spacing: float, dot_diameter: float,
         angle_deg: float = 0.0) -> CrossSection:
    d = dot_diameter
    unit = circle(d).translate((-d / 2, d / 2))  # center the dot on the tile point
    tiles: List[CrossSection] = [
        unit.translate(p) for p in tile_positions(region, spacing, angle_deg, stagger=True)]
    if not tiles:
        return CrossSection()
    pattern = CrossSection.batch_boolean(tiles, OpType.Add)
    return pattern ^ region


def lines(region: CrossSection, spacing: float, line_width: float,
          angle_deg: float = 45.0) -> CrossSection:
    if spacing <= 0:
        raise PatternDensityError("pattern spacing must be > 0")
    cx, cy, diag = _region_frame(region, angle_deg)
    if diag / spacing > MAX_TILES:
        raise PatternDensityError(
            f"pattern needs ~{int(diag / spacing):,} stripes "
            f"(max {MAX_TILES:,}) — increase the spacing")
    n = max(1, int(math.ceil(diag / spacing)) + 1)
    stripes: List[List[Point]] = []
    half = diag / 2 + spacing
    for i in range(-n, n + 1):
        off = i * spacing
        stripes.append([
            (-half, off - line_width / 2), (half, off - line_width / 2),
            (half, off + line_width / 2), (-half, off + line_width / 2),
        ])
    pattern = (CrossSection(stripes, fillrule=FillRule.Positive)
               .rotate(angle_deg)
               .translate((cx, cy)))
    return pattern ^ region


def grid(region: CrossSection, spacing: float, line_width: float,
         angle_deg: float = 0.0) -> CrossSection:
    return (lines(region, spacing, line_width, angle_deg)
            + lines(region, spacing, line_width, angle_deg + 90.0))


def hex_grid(region: CrossSection, spacing: float, line_width: float) -> CrossSection:
    """Honeycomb: three line families at 0/60/120°."""
    return (lines(region, spacing, line_width, 0.0)
            + lines(region, spacing, line_width, 60.0)
            + lines(region, spacing, line_width, 120.0))


def repeat_color_shapes(region: CrossSection,
                        color_shapes: "dict[str, CrossSection]",
                        spacing: float, angle_deg: float = 0.0,
                        spacing_y: float | None = None) -> "dict[str, CrossSection]":
    """Tile a multi-color unit (e.g. an SVG motif) across the region.

    All colors share one centering/rotation frame (the union bounding box)
    and the same tile positions, so their relative placement inside the
    motif is preserved on every tile.
    """
    if not color_shapes:
        return {}
    bs = [cs.bounds() for cs in color_shapes.values()]
    min_x, min_y = min(b[0] for b in bs), min(b[1] for b in bs)
    max_x, max_y = max(b[2] for b in bs), max(b[3] for b in bs)
    off = (-(min_x + max_x) / 2, -(min_y + max_y) / 2)
    # Margin covers the motif extent so overlapping tiles (gap < 0) whose
    # center falls just outside the region are not dropped.
    m = max(spacing, spacing_y or spacing, max_x - min_x, max_y - min_y)
    positions = list(tile_positions(region, spacing, angle_deg, stagger=True,
                                    spacing_y=spacing_y, margin=m))
    out: "dict[str, CrossSection]" = {}
    for color, unit in color_shapes.items():
        centered = unit.translate(off)
        if angle_deg:
            centered = centered.rotate(angle_deg)
        tiles = [centered.translate(p) for p in positions]
        if not tiles:
            continue
        pattern = CrossSection.batch_boolean(tiles, OpType.Add) ^ region
        if not pattern.is_empty():
            out[color] = pattern
    return out


def repeat_shape(region: CrossSection, unit: CrossSection, spacing: float,
                 angle_deg: float = 0.0,
                 spacing_y: float | None = None) -> CrossSection:
    """Tile an arbitrary unit shape (e.g. shaped text) across the region.

    The unit is centered on each tile point and rotated with the grid so the
    motif follows the pattern angle (v1 text-repeat semantics). `spacing_y`
    controls the distance between rows and defaults to `spacing`.
    """
    u_min_x, u_min_y, u_max_x, u_max_y = unit.bounds()
    centered = unit.translate((-(u_min_x + u_max_x) / 2, -(u_min_y + u_max_y) / 2))
    if angle_deg:
        centered = centered.rotate(angle_deg)
    m = max(spacing, spacing_y or spacing,
            u_max_x - u_min_x, u_max_y - u_min_y)
    tiles = [centered.translate(p)
             for p in tile_positions(region, spacing, angle_deg, stagger=True,
                                     spacing_y=spacing_y, margin=m)]
    if not tiles:
        return CrossSection()
    pattern = CrossSection.batch_boolean(tiles, OpType.Add)
    return pattern ^ region
