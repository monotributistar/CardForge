"""SVG → per-color CrossSections. Multicolor icons: each fill color can map
to a different document material.

Uses svgelements: resolves transforms, nested groups, and shape→path
conversion. Curves are flattened by uniform sampling per subpath.

Stroke-only artwork (Feather/Lucide-style icons) is supported: strokes are
converted to filled polygons (round caps/joins), keyed by the stroke color.
"""

from __future__ import annotations

import math
from functools import lru_cache
from io import StringIO
from typing import Dict, List, Tuple

from manifold3d import CrossSection, FillRule
from svgelements import SVG, Close, Line, Move, Path as SvgPath, Shape

Point = Tuple[float, float]

SAMPLES_PER_SEGMENT = 12
_JOIN_SIDES = 16  # circle approximation for stroke caps/joins


class SVGParseError(Exception):
    pass


def _path_contours(path: SvgPath) -> List[List[Point]]:
    """Flatten a path by sampling each SEGMENT in closed form.

    Never goes through Path.point(t): that maps t by arc length, which
    computes every segment's length via recursive quadrature — hundreds of
    ms for a single detailed icon. Per-segment evaluation is exact for
    lines and a direct polynomial for curves.
    """
    contours: List[List[Point]] = []
    for sub in path.as_subpaths():
        sp = SvgPath(sub)
        pts: List[Point] = []
        for seg in sp:
            if isinstance(seg, Move):
                if seg.end is not None:
                    pts.append((float(seg.end.x), float(seg.end.y)))
                continue
            if seg.end is None:
                continue
            if isinstance(seg, (Line, Close)):
                pts.append((float(seg.end.x), float(seg.end.y)))
            else:  # Quadratic/Cubic Bezier, Arc — closed-form point(t)
                for i in range(1, SAMPLES_PER_SEGMENT + 1):
                    pt = seg.point(i / SAMPLES_PER_SEGMENT)
                    pts.append((float(pt.x), float(pt.y)))
        if len(pts) >= 3:
            contours.append(pts)
    return contours


def _sample_subpaths(path: SvgPath) -> List[Tuple[List[Point], bool]]:
    """Flatten a path into (polyline, closed) per subpath — same per-segment
    sampling as _path_contours, but keeps open/closed so strokes can decide
    whether to join the last point back to the first."""
    out: List[Tuple[List[Point], bool]] = []
    for sub in path.as_subpaths():
        sp = SvgPath(sub)
        pts: List[Point] = []
        closed = False
        for seg in sp:
            if isinstance(seg, Move):
                if seg.end is not None:
                    pts.append((float(seg.end.x), float(seg.end.y)))
                continue
            if isinstance(seg, Close):
                closed = True
                continue
            if seg.end is None:
                continue
            if isinstance(seg, Line):
                pts.append((float(seg.end.x), float(seg.end.y)))
            else:  # Bezier / Arc — closed-form point(t)
                for i in range(1, SAMPLES_PER_SEGMENT + 1):
                    pt = seg.point(i / SAMPLES_PER_SEGMENT)
                    pts.append((float(pt.x), float(pt.y)))
        if len(pts) >= 2:
            out.append((pts, closed))
    return out


def _ccw(contour: List[Point]) -> List[Point]:
    """Force counter-clockwise winding (positive signed area)."""
    area = sum((x2 - x1) * (y2 + y1)
               for (x1, y1), (x2, y2) in zip(contour, contour[1:] + contour[:1]))
    return contour if area <= 0 else contour[::-1]


def _stroke_contours(path: SvgPath, stroke_width: float) -> List[List[Point]]:
    """Stroke a path into filled CCW contours: one quad per polyline segment
    plus a circle at every vertex (round caps and joins). Meant for a
    CrossSection with FillRule.Positive, where consistent CCW == union."""
    half = max(stroke_width, 1e-6) / 2
    circle = [(half * math.cos(2 * math.pi * i / _JOIN_SIDES),
               half * math.sin(2 * math.pi * i / _JOIN_SIDES))
              for i in range(_JOIN_SIDES)]
    contours: List[List[Point]] = []
    for pts, closed in _sample_subpaths(path):
        segs = list(zip(pts, pts[1:]))
        if closed and len(pts) >= 3:
            segs.append((pts[-1], pts[0]))
        for (x1, y1), (x2, y2) in segs:
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 1e-9:
                continue
            nx, ny = -dy / length * half, dx / length * half
            contours.append(_ccw([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                                  (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]))
        for (px, py) in pts:
            contours.append([(px + cx, py + cy) for cx, cy in circle])
    return contours


def _transform_scale(el: Shape) -> float:
    """Uniform scale factor an element's accumulated transform applies to
    its stroke width (sqrt of |det| — exact for uniform scale/rotation)."""
    m = getattr(el, "transform", None)
    if m is None:
        return 1.0
    det = float(m.a) * float(m.d) - float(m.b) * float(m.c)
    return math.sqrt(abs(det)) or 1.0


@lru_cache(maxsize=64)
def svg_to_color_shapes(svg_source: str, target_width: float,
                        target_height: float = 0.0) -> Dict[str, CrossSection]:
    """Parse SVG markup → {fill_hex → CrossSection}. Cached — Studio
    recompiles on every edit and the SVG source rarely changes; callers
    must treat the returned CrossSections as immutable (they are: every
    manifold3d op returns a new object).

    Output is feature-local (anchor at the artwork's top-left, y-up), scaled
    so the artwork's bounding box width == target_width (aspect preserved
    unless target_height is given).

    Fills with `none` or missing are skipped. Fill-rule holes are honored
    per paint layer via EvenOdd. Stroked shapes (with or without a fill)
    contribute their stroke as a filled polygon keyed by the stroke color.

    The painter's model is honored: each color's shape is its VISIBLE
    region — later-painted elements occlude earlier ones — so the returned
    regions are pairwise disjoint and extrude to what the artwork shows.
    """
    try:
        svg = SVG.parse(StringIO(svg_source))
    except Exception as e:
        raise SVGParseError(f"Cannot parse SVG: {e}") from e

    # Paint layers in document order: fill then stroke per element
    layers: List[Tuple[str, List[List[Point]], FillRule]] = []
    for el in svg.elements():
        if not isinstance(el, Shape):
            continue
        path = abs(SvgPath(el))  # abs() bakes in the accumulated transform
        if el.fill is not None and el.fill.value is not None:
            contours = _path_contours(path)
            if contours:
                layers.append((el.fill.hexrgb.lower(), contours, FillRule.EvenOdd))
        if el.stroke is not None and el.stroke.value is not None:
            sw = float(el.stroke_width or 1.0) * _transform_scale(el)
            if sw > 0:
                contours = _stroke_contours(path, sw)
                if contours:
                    # stroke quads/joins overlap heavily: union via Positive
                    # (all contours are CCW by construction)
                    layers.append((el.stroke.hexrgb.lower(), contours,
                                   FillRule.Positive))

    if not layers:
        return {}

    # Common bounding box across all layers so relative placement is kept
    all_pts = [pt for _, cts, _ in layers for ct in cts for pt in ct]
    min_x = min(x for x, _ in all_pts)
    max_x = max(x for x, _ in all_pts)
    min_y = min(y for _, y in all_pts)
    max_y = max(y for _, y in all_pts)
    w, h = max_x - min_x, max_y - min_y
    if w <= 0:
        return {}
    sx = target_width / w
    sy = (target_height / h) if (target_height and h > 0) else sx

    # Painter's model, back to front: a layer's visible region is its shape
    # minus everything painted after it.
    by_color: Dict[str, CrossSection] = {}
    cover = CrossSection()
    for color, contours, rule in reversed(layers):
        cs = CrossSection(contours, fillrule=rule)
        visible = cs - cover
        if not visible.is_empty():
            by_color[color] = by_color.get(color, CrossSection()) + visible
        cover = cover + cs

    out: Dict[str, CrossSection] = {}
    for color, cs in by_color.items():
        # normalize to origin → scale → flip SVG y-down into local y-up
        cs = (cs.translate((-min_x, -min_y))
                .scale((sx, sy))
                .mirror((0, 1))
                .simplify())
        if not cs.is_empty():
            out[color] = cs
    return out


def load_svg_file(path: str) -> str:
    from pathlib import Path as P

    p = P(path)
    if not p.exists():
        raise SVGParseError(f"SVG asset not found: {path}")
    return p.read_text(encoding="utf-8")
