"""2D shape builders — outlines and primitive feature shapes.

All builders return CrossSections in feature-local space (y-up, anchor at
(0,0), content in x ∈ [0,w], y ∈ [−h,0]) unless stated otherwise. `place()`
moves a local shape into physical space.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from manifold3d import CrossSection, FillRule

ARC_SEGMENTS = 16  # per 90° arc — <0.5% area error on typical card radii

Point = Tuple[float, float]


def _cs(contours: Sequence[Sequence[Point]]) -> CrossSection:
    return CrossSection(list(contours), fillrule=FillRule.EvenOdd)


# ── Primitives (feature-local: anchor top-left at origin, y-up) ────────────

def rect(width: float, height: float) -> CrossSection:
    return _cs([[(0, -height), (width, -height), (width, 0), (0, 0)]])


def rounded_rect(width: float, height: float, radius: float,
                 segments: int = ARC_SEGMENTS) -> CrossSection:
    r = max(0.0, min(radius, width / 2, height / 2))
    if r == 0:
        return rect(width, height)
    cx = {"l": r, "r": width - r}
    cy = {"t": -r, "b": -height + r}
    corners = [  # (center, start angle) counter-clockwise from right edge
        ((cx["r"], cy["t"]), 0.0),
        ((cx["l"], cy["t"]), math.pi / 2),
        ((cx["l"], cy["b"]), math.pi),
        ((cx["r"], cy["b"]), 3 * math.pi / 2),
    ]
    pts: List[Point] = []
    for (ccx, ccy), a0 in corners:
        for i in range(segments + 1):
            a = a0 + (math.pi / 2) * i / segments
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return _cs([pts])


def rounded_rect_corners(width: float, height: float,
                         tl: float, tr: float, br: float, bl: float,
                         segments: int = ARC_SEGMENTS) -> CrossSection:
    """Rectangle with an independent radius per corner (0 = sharp).

    Lets an outline be, e.g., three curved corners and one square.
    """
    def clamp(r: float) -> float:
        return max(0.0, min(r, width / 2, height / 2))

    tl, tr, br, bl = clamp(tl), clamp(tr), clamp(br), clamp(bl)
    pts: List[Point] = []

    def arc(cx: float, cy: float, r: float, a0: float, corner: Point) -> None:
        if r == 0:
            pts.append(corner)
            return
        for i in range(segments + 1):
            a = a0 + (math.pi / 2) * i / segments
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    # counter-clockwise from the top-right corner (local y-up, top at 0)
    arc(width - tr, -tr, tr, 0.0, (width, 0))
    arc(tl, -tl, tl, math.pi / 2, (0, 0))
    arc(bl, -height + bl, bl, math.pi, (0, -height))
    arc(width - br, -height + br, br, 3 * math.pi / 2, (width, -height))
    return _cs([pts])


def circle(diameter: float, segments: int = 4 * ARC_SEGMENTS) -> CrossSection:
    """Circle inscribed in its bounding box (anchor = box top-left)."""
    r = diameter / 2
    pts = [(r + r * math.cos(2 * math.pi * i / segments),
            -r + r * math.sin(2 * math.pi * i / segments))
           for i in range(segments)]
    return _cs([pts])


def ring(diameter: float, stroke_width: float) -> CrossSection:
    outer = circle(diameter)
    inner_d = max(0.0, diameter - 2 * stroke_width)
    if inner_d <= 0:
        return outer
    inner = circle(inner_d).translate((stroke_width, -stroke_width))
    return outer - inner


def frame(width: float, height: float, stroke_width: float,
          radius: float = 0.0) -> CrossSection:
    """Rectangular frame (border band) of the given outer size."""
    outer = rounded_rect(width, height, radius)
    iw, ih = width - 2 * stroke_width, height - 2 * stroke_width
    if iw <= 0 or ih <= 0:
        return outer
    inner = rounded_rect(iw, ih, max(0.0, radius - stroke_width))
    return outer - inner.translate((stroke_width, -stroke_width))


def corner_marks(width: float, height: float, length: float,
                 stroke_width: float) -> CrossSection:
    """Four L-shaped marks at the corners of a width×height box."""
    ln, sw = length, stroke_width
    # One L at top-left (local y-up): horizontal arm + vertical arm
    l_shape = rect(ln, sw) + rect(sw, ln)
    tl = l_shape
    tr = l_shape.mirror((1, 0)).translate((width, 0))
    bl = l_shape.mirror((0, 1)).translate((0, -height))
    br = l_shape.mirror((1, 0)).mirror((0, 1)).translate((width, -height))
    return tl + tr + bl + br


def svg_path(path_d: str, target_width: float, target_height: float = 0.0,
             tolerance_points: int = 24) -> CrossSection:
    """A single SVG path `d` string → CrossSection, scaled to target size.

    Used for `path` outlines and `shape` features with shapeType=path.
    SVG y-down space is flipped into local y-up.
    """
    from svgelements import Path as SvgPath

    p = SvgPath(path_d)
    contours: List[List[Point]] = []
    for sub in p.as_subpaths():
        sp = SvgPath(sub)
        if len(sp) == 0:
            continue
        n = max(8, tolerance_points * len(sp))
        pts = [sp.point(i / (n - 1)) for i in range(n)]
        contours.append([(pt.x, pt.y) for pt in pts])
    if not contours:
        return CrossSection()
    cs = _cs(contours)
    lo, hi = cs.bounds()[:2], cs.bounds()[2:]
    w, h = hi[0] - lo[0], hi[1] - lo[1]
    if w <= 0:
        return CrossSection()
    scale = target_width / w
    if target_height and h > 0:
        sy = target_height / h
    else:
        sy = scale
    # normalize to origin, scale, flip y-down → y-up with top at 0
    return (cs.translate((-lo[0], -lo[1]))
              .scale((scale, sy))
              .mirror((0, 1))
              .simplify())


# ── Placement: feature-local → physical space ──────────────────────────────

def place(cs: CrossSection, phys_x: float, phys_y: float,
          rotation_deg: float = 0.0, scale: float = 1.0) -> CrossSection:
    """Place a feature-local shape at a physical anchor point.

    Rotation is counter-clockwise around the SHAPE'S bounding-box center —
    the same pivot the 2D editor uses — so a rotated feature stays in place
    instead of swinging around its anchor. Scale is uniform.
    """
    out = cs
    if scale != 1.0:
        out = out.scale((scale, scale))
    if rotation_deg:
        b = out.bounds()
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        out = (out.translate((-cx, -cy))
                  .rotate(rotation_deg)
                  .translate((cx, cy)))
    return out.translate((phys_x, phys_y))


def bounds_of(cs: CrossSection) -> Tuple[float, float, float, float]:
    """(min_x, min_y, max_x, max_y) of a CrossSection."""
    b = cs.bounds()
    return (b[0], b[1], b[2], b[3])
