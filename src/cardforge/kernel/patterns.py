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


def _region_frame(region: CrossSection, angle_deg: float):
    """Iteration frame covering the region's bounds even when rotated."""
    min_x, min_y, max_x, max_y = region.bounds()
    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
    # Diagonal covers any rotation of the bounds
    diag = math.hypot(max_x - min_x, max_y - min_y)
    return cx, cy, diag


def tile_positions(region: CrossSection, spacing: float,
                   angle_deg: float = 0.0, stagger: bool = False) -> Iterator[Point]:
    """Yield tile centers on a (possibly rotated, possibly staggered) grid
    covering `region`. Centers outside the region are still yielded — the
    caller clips real geometry; for cheap filtering use region.bounds().
    """
    cx, cy, diag = _region_frame(region, angle_deg)
    n = max(1, int(math.ceil(diag / spacing)) + 1)
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)          # row direction
    vx, vy = -math.sin(a), math.cos(a)         # column direction
    for j in range(-n, n + 1):
        row_offset = (spacing / 2 if (stagger and j % 2) else 0.0)
        for i in range(-n, n + 1):
            px = cx + (i * spacing + row_offset) * ux + j * spacing * vx
            py = cy + (i * spacing + row_offset) * uy + j * spacing * vy
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
    cx, cy, diag = _region_frame(region, angle_deg)
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


def repeat_shape(region: CrossSection, unit: CrossSection, spacing: float,
                 angle_deg: float = 0.0) -> CrossSection:
    """Tile an arbitrary unit shape (e.g. shaped text) across the region.

    The unit is centered on each tile point and rotated with the grid so the
    motif follows the pattern angle (v1 text-repeat semantics).
    """
    u_min_x, u_min_y, u_max_x, u_max_y = unit.bounds()
    centered = unit.translate((-(u_min_x + u_max_x) / 2, -(u_min_y + u_max_y) / 2))
    if angle_deg:
        centered = centered.rotate(angle_deg)
    tiles = [centered.translate(p)
             for p in tile_positions(region, spacing, angle_deg, stagger=True)]
    if not tiles:
        return CrossSection()
    pattern = CrossSection.batch_boolean(tiles, OpType.Add)
    return pattern ^ region
