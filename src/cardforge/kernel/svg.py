"""SVG → per-color CrossSections. Multicolor icons: each fill color can map
to a different document material.

Uses svgelements: resolves transforms, nested groups, and shape→path
conversion. Curves are flattened by uniform sampling per subpath.
"""

from __future__ import annotations

from io import StringIO
from typing import Dict, List, Tuple

from manifold3d import CrossSection, FillRule
from svgelements import SVG, Path as SvgPath, Shape

Point = Tuple[float, float]

SAMPLES_PER_SEGMENT = 12


class SVGParseError(Exception):
    pass


def _path_contours(path: SvgPath) -> List[List[Point]]:
    contours: List[List[Point]] = []
    for sub in path.as_subpaths():
        sp = SvgPath(sub)
        seg_count = len(sp)
        if seg_count == 0:
            continue
        n = max(8, SAMPLES_PER_SEGMENT * seg_count)
        pts = []
        for i in range(n):
            pt = sp.point(i / (n - 1))
            if pt is not None:
                pts.append((float(pt.x), float(pt.y)))
        if len(pts) >= 3:
            contours.append(pts)
    return contours


def svg_to_color_shapes(svg_source: str, target_width: float,
                        target_height: float = 0.0) -> Dict[str, CrossSection]:
    """Parse SVG markup → {fill_hex → CrossSection}.

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
