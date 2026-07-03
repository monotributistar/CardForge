#!/usr/bin/env python3
"""Phase 0 kernel spike — validates every load-bearing library assumption.

Throwaway script. Each numbered check prints PASS/FAIL; exits 1 on any FAIL.
"""

import sys
import time
from io import StringIO
from pathlib import Path

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


# ── 1. manifold3d import + basic volume ──────────────────────────────────
try:
    from manifold3d import Manifold, CrossSection, FillRule

    cube = Manifold.cube((10, 10, 10))
    vol = cube.volume()
    check("1. manifold3d wheels + cube volume", abs(vol - 1000.0) < 1e-6, f"volume={vol}")
except Exception as e:
    check("1. manifold3d wheels + cube volume", False, repr(e))
    print("\nCannot continue without manifold3d."); sys.exit(1)


# ── Font helpers (prototype for kernel/text.py) ──────────────────────────
def flatten_recording(pen_value, steps: int = 12) -> list[list[tuple[float, float]]]:
    """Flatten a RecordingPen value into polygon contours."""
    contours: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    last = (0.0, 0.0)

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
            if current:
                contours.append(current)
            current = [args[0]]
            last = args[0]
        elif op == "lineTo":
            current.append(args[0])
            last = args[0]
        elif op == "qCurveTo":
            # TrueType: sequence of off-curves with implied on-curve midpoints
            pts = list(args)
            if pts[-1] is None:  # closed all-offcurve contour (rare)
                pts[-1] = current[0]
            offs, end = pts[:-1], pts[-1]
            p0 = last
            for i, off in enumerate(offs):
                nxt = offs[i + 1] if i + 1 < len(offs) else end
                seg_end = nxt if i + 1 == len(offs) else ((off[0] + nxt[0]) / 2, (off[1] + nxt[1]) / 2)
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
            if current:
                contours.append(current)
            current = []
    if current:
        contours.append(current)
    return contours


def signed_area(contour) -> float:
    a = 0.0
    n = len(contour)
    for i in range(n):
        x1, y1 = contour[i]
        x2, y2 = contour[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2


# ── 2. fonttools: glyph 'o' → 2 contours, opposite winding ───────────────
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Verdana.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/Library/Fonts/Arial.ttf",
]
font_path = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)
o_contours = None
try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import RecordingPen

    assert font_path, f"no static TTF found among {FONT_CANDIDATES}"
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    pen = RecordingPen()
    glyph_set[cmap[ord("o")]].draw(pen)
    o_contours = flatten_recording(pen.value)
    areas = [signed_area(c) for c in o_contours]
    windings_opposite = len(o_contours) == 2 and (areas[0] * areas[1] < 0)
    check("2. fonttools 'o' → 2 contours opposite winding",
          windings_opposite,
          f"font={Path(font_path).name} contours={len(o_contours)} areas={[round(a) for a in areas]}")
except Exception as e:
    check("2. fonttools 'o' → 2 contours opposite winding", False, repr(e))


# ── 3. CrossSection EvenOdd: the hole survives extrusion ─────────────────
try:
    assert o_contours and len(o_contours) == 2
    cs_holed = CrossSection(o_contours, fillrule=FillRule.EvenOdd)
    cs_filled = CrossSection([max(o_contours, key=lambda c: abs(signed_area(c)))],
                             fillrule=FillRule.EvenOdd)
    solid_holed = cs_holed.extrude(10.0)
    solid_filled = cs_filled.extrude(10.0)
    genus = solid_holed.genus()
    hole_ok = genus == 1 and solid_holed.volume() < solid_filled.volume() * 0.95
    check("3. CrossSection EvenOdd hole survives extrude",
          hole_ok,
          f"genus={genus} vol_holed={solid_holed.volume():.0f} vol_filled={solid_filled.volume():.0f}")
except Exception as e:
    check("3. CrossSection EvenOdd hole survives extrude", False, repr(e))


# ── 4. Variable font instancing: two weights → different areas ───────────
VAR_CANDIDATES = [
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/SFNSRounded.ttf",
    "/System/Library/Fonts/Supplemental/NewYork.ttf",
    "/System/Library/Fonts/SFCompact.ttf",
]
try:
    from fontTools.varLib.instancer import instantiateVariableFont

    var_path = None
    for p in VAR_CANDIDATES:
        if Path(p).exists():
            f = TTFont(p)
            if "fvar" in f:
                var_path = p
                var_font_axes = [a.axisTag for a in f["fvar"].axes]
                f.close()
                break
            f.close()
    assert var_path, f"no variable font found among {VAR_CANDIDATES}"

    def glyph_area_at_weight(path: str, wght: float) -> float:
        f = TTFont(path)
        instantiateVariableFont(f, {"wght": wght}, inplace=True)
        gs = f.getGlyphSet()
        cm = f.getBestCmap()
        pen = RecordingPen()
        gs[cm[ord("H")]].draw(pen)
        cts = flatten_recording(pen.value)
        cs = CrossSection(cts, fillrule=FillRule.EvenOdd)
        return cs.area()

    a300 = glyph_area_at_weight(var_path, 300)
    a700 = glyph_area_at_weight(var_path, 700)
    check("4. variable font instancing wght 300 vs 700",
          a700 > a300 * 1.15,
          f"font={Path(var_path).name} axes={var_font_axes} area300={a300:.0f} area700={a700:.0f}")
except Exception as e:
    check("4. variable font instancing wght 300 vs 700", False, repr(e))


# ── 4b. uharfbuzz shaping: kerning applied for 'AV' ──────────────────────
try:
    import uharfbuzz as hb

    blob = hb.Blob.from_file_path(font_path)
    face = hb.Face(blob)
    hb_font = hb.Font(face)

    def shaped_advance(text: str) -> float:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf)
        return sum(pos.x_advance for pos in buf.glyph_positions)

    av = shaped_advance("AV")
    a_v = shaped_advance("A") + shaped_advance("V")
    check("4b. uharfbuzz kerning 'AV' < 'A'+'V'", av < a_v, f"AV={av} A+V={a_v}")
except Exception as e:
    check("4b. uharfbuzz kerning 'AV' < 'A'+'V'", False, repr(e))


# ── 5. svgelements: 2-color SVG → 2 color-keyed shape groups ─────────────
try:
    from svgelements import SVG, Path as SvgPath, Shape

    two_color_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10">
      <rect x="0" y="0" width="10" height="10" fill="#ff0000"/>
      <g transform="translate(10,0)">
        <circle cx="5" cy="5" r="5" fill="#0000ff"/>
      </g>
    </svg>"""
    svg = SVG.parse(StringIO(two_color_svg))
    by_color: dict[str, list] = {}
    for el in svg.elements():
        if isinstance(el, Shape) and el.fill is not None and el.fill.value is not None:
            path = abs(SvgPath(el))  # abs() applies transforms
            by_color.setdefault(el.fill.hexrgb, []).append(path)
    colors = sorted(by_color.keys())
    # Convert one path to polygon points to prove geometry access works
    circle_path = by_color.get("#0000ff", [None])[0]
    npts = len([circle_path.point(i / 23) for i in range(24)]) if circle_path else 0
    # Verify the transform was applied: circle center should be at x≈15 (10 + 5)
    cx = sum(p.x for p in (circle_path.point(i / 23) for i in range(24))) / 24 if circle_path else 0
    check("5. svgelements 2-color SVG → 2 color groups",
          colors == ["#0000ff", "#ff0000"] and npts > 10 and 13 < cx < 17,
          f"colors={colors} circle_pts={npts} circle_cx={cx:.1f} (transform applied)")
except Exception as e:
    check("5. svgelements 2-color SVG → 2 color groups", False, repr(e))


# ── 7. Timing: QR 33x33 + 200-glyph text block < 100 ms ─────────────────
try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M

    t0 = time.perf_counter()

    # QR: matrix → module squares → one CrossSection (Positive fill = union of disjoint rects)
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=1, border=0)
    qr.add_data("https://cardforge.example.com/spike")
    qr.make(fit=True)
    n = qr.modules_count
    mm = 24.0 / n
    squares = []
    for r in range(n):
        for c in range(n):
            if qr.modules[r][c]:
                x, y = c * mm, r * mm
                squares.append([(x, y), (x + mm, y), (x + mm, y + mm), (x, y + mm)])
    qr_cs = CrossSection(squares, fillrule=FillRule.Positive)
    qr_solid = qr_cs.extrude(0.4)

    # Text: 200 glyphs flattened + extruded
    gs = font.getGlyphSet()
    cm = font.getBestCmap()
    text = ("CardForge kernel spike 0123456789 " * 6)[:200]
    all_contours = []
    x_cursor = 0.0
    upem = font["head"].unitsPerEm
    scale = 4.0 / upem  # 4mm font
    for ch in text:
        gname = cm.get(ord(ch))
        if not gname:
            continue
        pen = RecordingPen()
        gs[gname].draw(pen)
        for ct in flatten_recording(pen.value, steps=8):
            all_contours.append([(x * scale + x_cursor, y * scale) for x, y in ct])
        x_cursor += gs[gname].width * scale
    text_cs = CrossSection(all_contours, fillrule=FillRule.EvenOdd)
    text_solid = text_cs.extrude(0.4)

    # Force evaluation (manifold is lazy)
    _ = qr_solid.volume() + text_solid.volume()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    check("7. timing QR 33x33 + 200-glyph text",
          elapsed_ms < 100,
          f"{elapsed_ms:.1f} ms  qr_modules={n}x{n} qr_vol={qr_solid.volume():.1f} text_tris={text_solid.num_tri()}")
except Exception as e:
    check("7. timing QR + text < 100ms", False, repr(e))


# ── Summary ───────────────────────────────────────────────────────────────
print()
fails = [r for r in RESULTS if not r[1]]
print(f"{'=' * 60}\n{len(RESULTS) - len(fails)}/{len(RESULTS)} checks passed")
sys.exit(1 if fails else 0)
