"""SVG → per-color CrossSections. Multicolor icons: each fill color can map
to a different document material.

Uses svgelements: resolves transforms, nested groups, and shape→path
conversion. Curves are flattened by uniform sampling per subpath.
"""

from __future__ import annotations

from functools import lru_cache
from io import StringIO
from typing import Dict, List, Tuple

from manifold3d import CrossSection, FillRule
from svgelements import SVG, Close, Line, Move, Path as SvgPath, Shape

Point = Tuple[float, float]

SAMPLES_PER_SEGMENT = 12


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
    per color group via EvenOdd.
    """
    try:
        svg = SVG.parse(StringIO(svg_source))
    except Exception as e:
        raise SVGParseError(f"Cannot parse SVG: {e}") from e

    by_color: Dict[str, List[List[Point]]] = {}
    for el in svg.elements():
        if not isinstance(el, Shape):
            continue
        if el.fill is None or el.fill.value is None:
            continue
        path = abs(SvgPath(el))  # abs() bakes in the accumulated transform
        contours = _path_contours(path)
        if contours:
            by_color.setdefault(el.fill.hexrgb.lower(), []).extend(contours)

    if not by_color:
        return {}

    # Common bounding box across all colors so relative placement is kept
    all_x = [x for cts in by_color.values() for ct in cts for x, _ in ct]
    all_y = [y for cts in by_color.values() for ct in cts for _, y in ct]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    w, h = max_x - min_x, max_y - min_y
    if w <= 0:
        return {}
    sx = target_width / w
    sy = (target_height / h) if (target_height and h > 0) else sx

    out: Dict[str, CrossSection] = {}
    for color, contours in by_color.items():
        cs = CrossSection(contours, fillrule=FillRule.EvenOdd)
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
    return p.read_text()
