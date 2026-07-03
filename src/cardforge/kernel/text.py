"""Text → CrossSection. Shaping via uharfbuzz, outlines via fontTools.

`text_block(...)` is the main entry: multi-line, aligned, kerned text as one
CrossSection in feature-local space (anchor at the block's top-left, y-up).
Font size is the em size in mm (same convention the 2D editor uses).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import uharfbuzz as hb
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from manifold3d import CrossSection, FillRule

from cardforge.kernel.fonts import load_font

Point = Tuple[float, float]

BEZIER_STEPS = 10  # flattening resolution; ~0.2% area error at card sizes


# ── Bezier flattening (font units) ─────────────────────────────────────────

def _flatten_pen(pen_value, steps: int = BEZIER_STEPS) -> List[List[Point]]:
    contours: List[List[Point]] = []
    current: List[Point] = []
    last: Point = (0.0, 0.0)

    def bez_q(p0, p1, p2, t):
        mt = 1 - t
        return (mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1])

    def bez_c(p0, p1, p2, p3, t):
        mt = 1 - t
        return (mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
                mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1])

    for op, args in pen_value:
        if op == "moveTo":
            if len(current) >= 3:
                contours.append(current)
            current = [args[0]]
            last = args[0]
        elif op == "lineTo":
            current.append(args[0])
            last = args[0]
        elif op == "qCurveTo":
            pts = list(args)
            if pts[-1] is None:  # all-off-curve closed contour
                pts[-1] = current[0] if current else (0.0, 0.0)
            offs, end = pts[:-1], pts[-1]
            p0 = last
            for i, off in enumerate(offs):
                if i + 1 < len(offs):
                    nxt = offs[i + 1]
                    seg_end = ((off[0] + nxt[0]) / 2, (off[1] + nxt[1]) / 2)
                else:
                    seg_end = end
                for s in range(1, steps + 1):
                    current.append(bez_q(p0, off, seg_end, s / steps))
                p0 = seg_end
            last = end
        elif op == "curveTo":
            c1, c2, end = args
            for s in range(1, steps + 1):
                current.append(bez_c(last, c1, c2, end, s / steps))
            last = end
        elif op == "closePath":
            if len(current) >= 3:
                contours.append(current)
            current = []
    if len(current) >= 3:
        contours.append(current)
    return contours


# ── Shaping ────────────────────────────────────────────────────────────────

@dataclass
class ShapedGlyph:
    glyph_name: str
    x_offset: float  # font units
    y_offset: float


def _shape_line(font: TTFont, hb_font: "hb.Font", text: str) -> Tuple[List[ShapedGlyph], float]:
    """Shape one line; returns positioned glyphs + total advance (font units)."""
    if not text:
        return [], 0.0
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)
    if not buf.glyph_infos:
        return [], 0.0

    glyph_order = font.getGlyphOrder()
    glyphs: List[ShapedGlyph] = []
    x = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = glyph_order[info.codepoint] if info.codepoint < len(glyph_order) else ".notdef"
        glyphs.append(ShapedGlyph(name, x + pos.x_offset, pos.y_offset))
        x += pos.x_advance
    return glyphs, x


def _make_hb_font(font: TTFont) -> "hb.Font":
    """Build an hb.Font from the (possibly instantiated) TTFont bytes."""
    import io

    buf = io.BytesIO()
    font.save(buf, reorderTables=False)
    face = hb.Face(buf.getvalue())
    return hb.Font(face)


# glyph-outline cache per TTFont identity: (id(font), glyph) → contours
_outline_cache: Dict[Tuple[int, str], List[List[Point]]] = {}


def _glyph_contours(font: TTFont, glyph_name: str) -> List[List[Point]]:
    key = (id(font), glyph_name)
    if key not in _outline_cache:
        pen = RecordingPen()
        try:
            font.getGlyphSet()[glyph_name].draw(pen)
            _outline_cache[key] = _flatten_pen(pen.value)
        except KeyError:
            _outline_cache[key] = []
    return _outline_cache[key]


# ── Public API ─────────────────────────────────────────────────────────────

@dataclass
class TextResult:
    cross_section: CrossSection
    width: float      # mm, widest line
    height: float     # mm, block height (baselines span + ascent/descent)
    line_count: int


def text_block(
    lines: List[str],
    family: str,
    size_mm: float,
    weight: Optional[float] = None,
    axes: Optional[Dict[str, float]] = None,
    align: str = "left",
    line_height: float = 1.4,
) -> TextResult:
    """Render a text block to one CrossSection (feature-local, y-up).

    Anchor: top-left of the block. The first line's ascent sits at y=0 and
    text extends downward (negative y), matching document semantics.
    """
    font, _face = load_font(family, weight=weight, axes=axes)
    hb_font = _make_hb_font(font)
    upem = font["head"].unitsPerEm
    scale = size_mm / upem
    ascent = font["hhea"].ascent * scale
    line_step = size_mm * line_height

    shaped: List[Tuple[List[ShapedGlyph], float]] = [
        _shape_line(font, hb_font, line) for line in lines]
    widths_mm = [adv * scale for _, adv in shaped]
    block_width = max(widths_mm) if widths_mm else 0.0

    all_contours: List[List[Point]] = []
    for li, (glyphs, adv) in enumerate(shaped):
        if align == "center":
            x0 = (block_width - widths_mm[li]) / 2
        elif align == "right":
            x0 = block_width - widths_mm[li]
        else:
            x0 = 0.0
        baseline_y = -ascent - li * line_step
        for g in glyphs:
            for contour in _glyph_contours(font, g.glyph_name):
                all_contours.append([
                    (x0 + (gx + g.x_offset) * scale,
                     baseline_y + (gy + g.y_offset) * scale)
                    for gx, gy in contour
                ])

    cs = (CrossSection(all_contours, fillrule=FillRule.EvenOdd).simplify()
          if all_contours else CrossSection())
    descent = abs(font["hhea"].descent) * scale
    block_height = ascent + descent + (len(lines) - 1) * line_step if lines else 0.0
    return TextResult(cs, block_width, block_height, len(lines))
