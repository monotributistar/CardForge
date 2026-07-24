"""Feature → placed 2D shapes per material (physical space).

`build_feature_shapes()` turns one schema-v2 feature into:
  - [(material_id, CrossSection)] in PHYSICAL space, front-face orientation
    (the compiler mirrors for the back face),
  - a FeatureRecord for the trace.

Missing assets and unresolvable content do not raise: they return an empty
shape list and a reason string so compilation degrades gracefully and the
editor can surface the problem as a warning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from manifold3d import CrossSection

from cardforge.document.schema_v2 import DocumentV2, Feature
from cardforge.kernel import patterns as pat
from cardforge.kernel import shapes2d as s2
from cardforge.kernel.measure import min_feature_width
from cardforge.kernel.qr import format_qr_payload, qr_cross_section
from cardforge.kernel.svg import SVGParseError, load_svg_file, svg_to_color_shapes
from cardforge.kernel.text import text_block
from cardforge.kernel.types import Bounds, FeatureRecord


@dataclass
class FeatureShapes:
    shapes: List[Tuple[str, CrossSection]] = field(default_factory=list)
    record: Optional[FeatureRecord] = None
    skip_reason: str = ""
    # Exclusion region (physical space): lower-priority features must not
    # place geometry here even where this feature has none (QR quiet zone).
    keepout: Optional[CrossSection] = None
    # hole feature with tab=true: material lug (physical space) the compiler
    # fuses into the base region — lets the hole live outside the outline.
    tab: Optional[CrossSection] = None


def _doc_to_phys_anchor(x: float, y: float, obj_h: float) -> Tuple[float, float]:
    """Document top-left-origin y-down → physical bottom-left-origin y-up."""
    return x, obj_h - y


def _phys_bounds_to_doc(cs: CrossSection, obj_h: float) -> Bounds:
    min_x, min_y, max_x, max_y = cs.bounds()
    return Bounds(min_x, obj_h - max_y, max_x - min_x, max_y - min_y)


def _outline_svg_shapes(doc: DocumentV2) -> Dict[str, CrossSection]:
    """Per-color shapes of an svgInline outline, feature-local (y ∈ [-H, 0])."""
    o = doc.object.outline
    try:
        return svg_to_color_shapes(o.svg_inline, o.width, o.height)
    except SVGParseError as e:
        raise ValueError(f"outline SVG cannot be parsed: {e}") from e


def outline_cross_section(doc: DocumentV2) -> CrossSection:
    """Object outline in physical space: x ∈ [0,W], y ∈ [0,H]."""
    o = doc.object.outline
    if o.type == "rect":
        local = s2.rect(o.width, o.height)
    elif o.type == "rounded-rect":
        if o.corners:
            c = o.corner_radii()
            local = s2.rounded_rect_corners(
                o.width, o.height, c["tl"], c["tr"], c["br"], c["bl"])
        else:
            local = s2.rounded_rect(o.width, o.height, o.radius)
    elif o.type == "circle":
        local = s2.circle(o.diameter or o.width)
    elif o.type == "path":
        if o.svg_inline:
            # Full SVG markup: the outline is the union of every colored
            # shape (the artwork's silhouette).
            local = CrossSection()
            for cs in _outline_svg_shapes(doc).values():
                local = local + cs
            if local.is_empty():
                raise ValueError("outline SVG has no fillable shapes")
        else:
            local = s2.svg_path(o.svg_path, o.width, o.height)
    else:
        raise ValueError(f"unknown outline type: {o.type}")
    return local.translate((0, o.height))


def outline_color_regions(doc: DocumentV2) -> List[Tuple[str, CrossSection]]:
    """Multicolor outline: [(material_id, region)] in PHYSICAL space for every
    SVG color mapped to a NON-base material via outline.colorMap. Regions not
    covered (or mapped to base) stay base material. Empty list when the
    outline isn't a multicolor SVG."""
    o = doc.object.outline
    if o.type != "path" or not o.svg_inline or not o.color_map:
        return []
    base_id = doc.base_material.id
    out: List[Tuple[str, CrossSection]] = []
    for color, cs in sorted(_outline_svg_shapes(doc).items()):
        mat = o.color_map.get(color)
        if mat and mat != base_id:
            out.append((mat, cs.translate((0, o.height))))
    return out


def build_feature_shapes(doc: DocumentV2, face_id: str, feature: Feature,
                         outline_phys: CrossSection,
                         asset_root: Path) -> FeatureShapes:
    obj_h = doc.object.outline.height
    f = feature
    px, py = _doc_to_phys_anchor(f.transform.x, f.transform.y, obj_h)
    rot = -f.transform.rotation  # doc rotation is screen-clockwise; phys is y-up
    scale = f.transform.scale
    extra: Dict[str, float] = {}

    def placed(local: CrossSection) -> CrossSection:
        return s2.place(local, px, py, rotation_deg=rot, scale=scale)

    shapes: List[Tuple[str, CrossSection]] = []
    keepout: Optional[CrossSection] = None

    if f.type == "text-block":
        try:
            result = text_block(
                f.lines, f.font.family, f.font.size,
                weight=f.font.weight, axes=f.font.axes, italic=f.font.italic,
                align=f.align, line_height=f.line_height,
            )
        except Exception as e:  # missing family, bitmap/corrupt font tables
            return FeatureShapes(
                skip_reason=f"font '{f.font.family}' cannot be rendered: {e}")
        extra["font_size"] = f.font.size
        shapes = [(f.material, placed(result.cross_section))]

    elif f.type == "text-pattern":
        try:
            unit = text_block([f.text], f.font.family, f.font.size,
                              weight=f.font.weight, axes=f.font.axes,
                              italic=f.font.italic).cross_section
        except Exception as e:
            return FeatureShapes(
                skip_reason=f"font '{f.font.family}' cannot be rendered: {e}")
        if unit.is_empty():
            return FeatureShapes(skip_reason="text-pattern rendered empty")
        # spacing is the GAP between repetitions, not the tile step — so the
        # pattern stays consistent when the text (and its width) changes.
        u0x, u0y, u1x, u1y = unit.bounds()
        step_x = (u1x - u0x) + f.spacing
        step_y = (u1y - u0y) + (f.spacing_y or f.spacing)
        cs = pat.repeat_shape(outline_phys, unit, step_x, angle_deg=-f.angle,
                              spacing_y=step_y)
        extra["font_size"] = f.font.size
        shapes = [(f.material, cs)]

    elif f.type == "pattern":
        if f.region == "face" or not (f.width and f.height):
            region = outline_phys
        else:
            region = placed(s2.rect(f.width, f.height)) ^ outline_phys
        if f.pattern_type == "svg":
            # SVG motif repeat — multicolor: each fill color can map to a
            # different material via colorMap (same contract as icon).
            if not f.svg_inline:
                return FeatureShapes(skip_reason="svg pattern has no SVG source")
            try:
                motif = svg_to_color_shapes(f.svg_inline, f.element_size or 6.0)
            except SVGParseError as e:
                return FeatureShapes(skip_reason=str(e))
            if not motif:
                return FeatureShapes(skip_reason="svg pattern has no filled shapes")
            # spacing = gap between motif repetitions (see text-pattern)
            bs = [cs.bounds() for cs in motif.values()]
            m_w = max(b[2] for b in bs) - min(b[0] for b in bs)
            m_h = max(b[3] for b in bs) - min(b[1] for b in bs)
            tiled = pat.repeat_color_shapes(region, motif, m_w + f.spacing,
                                            angle_deg=-f.angle,
                                            spacing_y=m_h + (f.spacing_y or f.spacing))
            if not tiled:
                return FeatureShapes(skip_reason="svg pattern rendered empty")
            extra["element_mm"] = f.element_size or 6.0
            extra["icon_colors"] = len(motif)
            for color, cs in sorted(tiled.items()):
                mat = f.color_map.get(color, f.material)
                shapes.append((mat, cs))
        elif f.pattern_type == "dots":
            d = f.element_size or f.spacing * 0.4
            cs = pat.dots(region, f.spacing, d, angle_deg=-f.angle)
            extra["element_mm"] = d
        elif f.pattern_type == "lines":
            w = f.element_size or 0.8
            cs = pat.lines(region, f.spacing, w, angle_deg=-f.angle or 45.0)
            extra["element_mm"] = w
        elif f.pattern_type == "grid":
            w = f.element_size or 0.8
            cs = pat.grid(region, f.spacing, w, angle_deg=-f.angle)
            extra["element_mm"] = w
        elif f.pattern_type == "hex":
            w = f.element_size or 0.6
            cs = pat.hex_grid(region, f.spacing, w)
            extra["element_mm"] = w
        else:
            return FeatureShapes(skip_reason=f"unknown patternType '{f.pattern_type}'")
        if f.pattern_type != "svg":  # svg already appended per-color shapes
            shapes = [(f.material, cs)]

    elif f.type == "qr":
        payload = format_qr_payload(f.qr_type, f.fields)
        if not payload:
            return FeatureShapes(skip_reason="qr payload empty")
        result = qr_cross_section(payload, f.size, f.quiet_zone, f.error_correction)
        extra["qr_modules"] = result.modules
        extra["qr_module_mm"] = result.module_mm
        extra["qr_quiet_mm"] = f.quiet_zone
        shapes = [(f.material, placed(result.cross_section))]
        # The full square INCLUDING the quiet zone is a keep-out: the quiet
        # zone must stay flat/uniform or the code stops scanning.
        total = f.size + 2 * f.quiet_zone
        keepout = placed(s2.rect(total, total))

    elif f.type == "icon":
        try:
            if f.svg_inline:
                source = f.svg_inline
            else:
                ref = f.svg_asset
                path = doc.assets.get(ref, ref)
                source = load_svg_file(str((asset_root / path)))
            color_shapes = svg_to_color_shapes(source, f.width, f.height)
        except SVGParseError as e:
            return FeatureShapes(skip_reason=str(e))
        if not color_shapes:
            return FeatureShapes(skip_reason="icon SVG has no filled shapes")
        for color, cs in sorted(color_shapes.items()):
            mat = f.color_map.get(color, f.material)
            shapes.append((mat, placed(cs)))
        extra["icon_colors"] = len(color_shapes)

    elif f.type == "shape":
        o = doc.object.outline
        if f.shape_type == "rect":
            local = s2.rect(f.width, f.height)
        elif f.shape_type == "rounded-rect":
            local = s2.rounded_rect(f.width, f.height, f.radius)
        elif f.shape_type == "circle":
            local = s2.circle(f.diameter or f.width)
        elif f.shape_type == "ring":
            local = s2.ring(f.diameter or f.width, f.stroke_width or 1.0)
        elif f.shape_type == "frame":
            w = f.width or (o.width - 2 * f.inset)
            h = f.height or (o.height - 2 * f.inset)
            local = s2.frame(w, h, f.stroke_width or 1.0, radius=f.radius)
            if not f.width:  # inset-relative to the outline, ignore transform
                px, py = _doc_to_phys_anchor(f.inset, f.inset, obj_h)
        elif f.shape_type == "corner-marks":
            w = f.width or (o.width - 2 * f.inset)
            h = f.height or (o.height - 2 * f.inset)
            local = s2.corner_marks(w, h, f.length or 6.0, f.stroke_width or 1.0)
            if not f.width:
                px, py = _doc_to_phys_anchor(f.inset, f.inset, obj_h)
        elif f.shape_type == "path":
            local = s2.svg_path(f.svg_path, f.width, f.height)
        else:
            return FeatureShapes(skip_reason=f"unknown shapeType '{f.shape_type}'")
        extra["shape_type"] = f.shape_type
        shapes = [(f.material, placed(local))]

    elif f.type == "hole":
        # Always a through-cut: circle (keyring) or slot (lanyard/credential
        # strap — a stadium: rounded-rect with full-radius ends).
        if f.hole_type == "circle":
            local = s2.circle(f.diameter or 5.0)
        elif f.hole_type == "slot":
            w, h = f.width or 14.0, f.height or 5.0
            local = s2.rounded_rect(w, h, h / 2)
        else:
            return FeatureShapes(skip_reason=f"unknown holeType '{f.hole_type}'")
        extra["hole_type"] = f.hole_type
        shapes = [(f.material, placed(local))]

    else:
        return FeatureShapes(skip_reason=f"unknown feature type '{f.type}'")

    # Non-empty union of everything this feature produced, for the record
    non_empty = [cs for _, cs in shapes if not cs.is_empty()]
    if not non_empty:
        return FeatureShapes(skip_reason="feature produced no geometry")
    union = non_empty[0]
    for cs in non_empty[1:]:
        union = union + cs

    # Thinnest printable detail (mm) — compared against the nozzle downstream.
    # Cuts are holes; their "width" isn't a printable wall, so skip.
    if f.relief.mode != "cut" and f.type != "hole":
        extra["min_width_mm"] = round(min_feature_width(union), 3)

    # Hole tab: the hole outline dilated by tabMargin (round join) — a lug
    # the compiler fuses into the base so the hole can sit past the edge.
    tab_cs: Optional[CrossSection] = None
    if f.type == "hole" and f.tab:
        tab_cs = union.offset(f.tab_margin or 3.0, 0)  # 0 = Round join

    # Solid content features claim their bounding box as keep-out, so tiled
    # backgrounds (text patterns, tramas) can't interleave with their glyphs.
    # QR set a wider box above (quiet zone); patterns/shapes claim nothing —
    # they ARE the background / decorative layers.
    if keepout is None and f.type in ("text-block", "icon"):
        bx0, by0, bx1, by1 = union.bounds()
        keepout = CrossSection([[(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]])

    relief_value = (f.relief.height if f.relief.mode == "emboss"
                    else 0.0 if f.relief.mode == "cut" else f.relief.depth)
    # A hole is a through-cut by definition, whatever relief the doc carries.
    relief_mode = "cut" if f.type == "hole" else f.relief.mode
    if f.type == "hole":
        relief_value = 0.0
    record = FeatureRecord(
        feature_id=f.id,
        face_id=face_id,
        type=f.type,
        material=f.material,
        relief_mode=relief_mode,
        relief_value=relief_value,
        bounds=_phys_bounds_to_doc(union, obj_h),
        area=sum(cs.area() for cs in non_empty),
        extra=extra,
    )
    return FeatureShapes(shapes=shapes, record=record, keepout=keepout, tab=tab_cs)
