"""Tests for stroke-SVG support and multicolor SVG outlines (svgInline)."""

import pytest

from cardforge.document.schema_v2 import (DocumentV2, SCHEMA_VERSION,
                                          DocumentValidationError, validate_v2)
from cardforge.kernel.compile import compile_document
from cardforge.kernel.features import outline_color_regions, outline_cross_section
from cardforge.kernel.svg import svg_to_color_shapes

MULTI_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">'
    '<rect width="100" height="60" rx="10" fill="#1a1a1a"/>'
    '<circle cx="30" cy="30" r="15" fill="#ff0000"/>'
    '<path d="M60 15 L90 15 L75 45 Z" fill="#00aaff"/>'
    '</svg>'
)

STROKE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
)


def _doc(outline: dict, materials=None, features=(), back=()) -> DocumentV2:
    return DocumentV2.from_dict({
        "cardforge": SCHEMA_VERSION,
        "meta": {"id": "t", "name": "t"},
        "object": {"outline": outline, "thickness": 2.0},
        "materials": materials or [
            {"id": "base", "name": "B", "color": "#1a1a1a", "slot": 1, "role": "base"},
            {"id": "red", "name": "R", "color": "#ff0000", "slot": 2},
            {"id": "blue", "name": "U", "color": "#00aaff", "slot": 3},
        ],
        "faces": {"front": {"features": list(features)},
                  "back": {"features": list(back)}},
    })


class TestStrokeSvg:
    def test_stroke_only_icon_renders(self):
        shapes = svg_to_color_shapes(STROKE_SVG, 20.0)
        assert "#000000" in shapes  # currentColor → black
        # a Ø20 ring with ~2.2mm stroke: area ≈ π·(r_out²−r_in²)
        assert 80 < shapes["#000000"].area() < 160

    def test_open_path_stroke_renders(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
               'fill="none" stroke="#ff0000" stroke-width="2">'
               '<path d="M4 4 L20 20"/></svg>')
        shapes = svg_to_color_shapes(svg, 20.0)
        assert list(shapes) == ["#ff0000"]
        assert shapes["#ff0000"].area() > 10

    def test_painters_model_occlusion(self):
        # A shape drawn ON TOP of another must punch its region out of the
        # one below — regions are disjoint, matching what the artwork shows.
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
               '<rect width="20" height="20" fill="#ff0000"/>'
               '<rect x="5" y="5" width="10" height="10" fill="#00ff00"/></svg>')
        shapes = svg_to_color_shapes(svg, 20.0)
        assert shapes["#00ff00"].area() == pytest.approx(100, rel=1e-3)
        assert shapes["#ff0000"].area() == pytest.approx(300, rel=1e-3)  # not 400
        assert (shapes["#ff0000"] ^ shapes["#00ff00"]).is_empty()

    def test_fill_plus_stroke_yields_both_colors(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
               '<rect x="4" y="4" width="16" height="16" fill="#00ff00" '
               'stroke="#0000ff" stroke-width="2"/></svg>')
        shapes = svg_to_color_shapes(svg, 20.0)
        assert set(shapes) == {"#00ff00", "#0000ff"}


class TestSvgInlineOutline:
    def test_silhouette_covers_all_colors(self):
        doc = _doc({"type": "path", "svgInline": MULTI_SVG,
                    "width": 80, "height": 48})
        cs = outline_cross_section(doc)
        min_x, min_y, max_x, max_y = cs.bounds()
        assert (max_x - min_x) == pytest.approx(80, abs=0.1)
        assert (max_y - min_y) == pytest.approx(48, abs=0.1)
        assert min_y == pytest.approx(0, abs=0.1)  # physical space y ∈ [0, H]

    def test_color_regions_skip_base_and_unmapped(self):
        doc = _doc({"type": "path", "svgInline": MULTI_SVG, "width": 80,
                    "height": 48,
                    "colorMap": {"#1a1a1a": "base", "#ff0000": "red"}})
        regions = outline_color_regions(doc)
        assert [m for m, _ in regions] == ["red"]  # base + unmapped excluded

    def test_compile_splits_base_per_material(self):
        doc = _doc({"type": "path", "svgInline": MULTI_SVG, "width": 80,
                    "height": 48,
                    "colorMap": {"#1a1a1a": "base", "#ff0000": "red",
                                 "#00aaff": "blue"}})
        scene, trace = compile_document(doc)
        parts = {p.id: p for p in scene.non_empty_parts()}
        assert {"base", "base:red", "base:blue"} <= set(parts)
        assert parts["base:red"].material == "red"
        # full-thickness columns: volume == region area × thickness
        assert parts["base:red"].solid.volume() > 100
        # disjoint partition: total == outline area × thickness
        total = sum(p.solid.volume() for p in parts.values())
        area = outline_cross_section(doc).area()
        assert total == pytest.approx(area * 2.0, rel=1e-3)

    def test_through_cut_pierces_colored_base(self):
        hole = {"id": "h", "type": "hole", "material": "base",
                "holeType": "circle", "diameter": 6,
                "transform": {"x": 30, "y": 24},
                "relief": {"mode": "cut"}}
        with_hole = _doc({"type": "path", "svgInline": MULTI_SVG, "width": 80,
                          "height": 48, "colorMap": {"#ff0000": "red"}},
                         features=[hole])
        without = _doc({"type": "path", "svgInline": MULTI_SVG, "width": 80,
                        "height": 48, "colorMap": {"#ff0000": "red"}})
        v_with = compile_document(with_hole)[0].volumes["red"].volume()
        v_without = compile_document(without)[0].volumes["red"].volume()
        assert v_with < v_without  # the hole carved the red column too

    def test_unknown_colormap_material_rejected(self):
        data = _doc({"type": "path", "svgInline": MULTI_SVG, "width": 80,
                     "height": 48}).to_dict()
        data["object"]["outline"]["colorMap"] = {"#ff0000": "nope"}
        with pytest.raises(DocumentValidationError, match="colorMap"):
            validate_v2(data)

    def test_color_depth_at_or_over_thickness_rejected(self):
        data = _doc({"type": "path", "svgInline": MULTI_SVG, "width": 80,
                     "height": 48, "colorMap": {"#ff0000": "red"}}).to_dict()
        data["object"]["outline"]["colorDepth"] = 2.0  # == thickness
        with pytest.raises(DocumentValidationError, match="colorDepth"):
            validate_v2(data)

    def test_svg_path_d_string_still_works(self):
        doc = _doc({"type": "path", "svgPath": "M0 0 H100 V60 H0 Z",
                    "width": 80, "height": 48})
        cs = outline_cross_section(doc)
        assert cs.area() == pytest.approx(80 * 48, rel=1e-3)


class TestColorLayer:
    """colorDepth/colorFace: the artwork's colors as a layer on one face,
    with base material behind it — so the other face is a clean canvas."""

    OUTLINE = {"type": "path", "svgInline": MULTI_SVG, "width": 80, "height": 48,
               "colorMap": {"#1a1a1a": "base", "#ff0000": "red", "#00aaff": "blue"}}

    def _doc(self, **extra):
        return _doc({**self.OUTLINE, **extra})

    @staticmethod
    def _slab(doc, z0: float, h: float):
        """Full-outline slab z ∈ [z0, z0+h] — a probe for what a face shows."""
        return outline_cross_section(doc).extrude(h).translate((0, 0, z0))

    @staticmethod
    def _parts(doc):
        return {p.id: p for p in compile_document(doc)[0].non_empty_parts()}

    def test_front_layer_sits_on_top_of_the_body(self):
        parts = self._parts(self._doc(colorDepth=0.6))
        bb = parts["base:red"].solid.bounding_box()
        assert (bb[2], bb[5]) == pytest.approx((1.4, 2.0), abs=1e-6)

    def test_back_face_stays_solid_base_material(self):
        doc = self._doc(colorDepth=0.6)
        parts = self._parts(doc)
        floor = self._slab(doc, 0.0, 0.2)   # the layers printed against the bed
        area = outline_cross_section(doc).area()
        assert (parts["base"].solid ^ floor).volume() == pytest.approx(area * 0.2,
                                                                      rel=1e-3)
        for pid in ("base:red", "base:blue"):
            assert (parts[pid].solid ^ floor).is_empty()

    def test_layer_volume_follows_the_declared_depth(self):
        v_thin = compile_document(self._doc(colorDepth=0.4))[0].volumes["red"].volume()
        v_thick = compile_document(self._doc(colorDepth=0.8))[0].volumes["red"].volume()
        assert v_thick == pytest.approx(2 * v_thin, rel=1e-3)

    def test_color_face_back_prints_the_colors_against_the_bed(self):
        bb = self._parts(self._doc(colorDepth=0.6,
                                   colorFace="back"))["base:red"].solid.bounding_box()
        assert (bb[2], bb[5]) == pytest.approx((0.0, 0.6), abs=1e-6)

    def test_color_face_both_leaves_base_in_the_middle(self):
        doc = self._doc(colorDepth=0.5, colorFace="both")
        red = self._parts(doc)["base:red"].solid
        assert not (red ^ self._slab(doc, 0.0, 0.1)).is_empty()   # bed side
        assert not (red ^ self._slab(doc, 1.9, 0.1)).is_empty()   # top side
        assert (red ^ self._slab(doc, 0.9, 0.2)).is_empty()       # base between

    def test_partition_stays_exact(self):
        doc = self._doc(colorDepth=0.6)
        scene, _ = compile_document(doc)
        total = sum(p.solid.volume() for p in scene.non_empty_parts())
        assert total == pytest.approx(outline_cross_section(doc).area() * 2.0,
                                      rel=1e-3)

    def test_back_inlay_leaves_the_front_colors_intact(self):
        # The point of the layer: a plate inlaid on the back carves base
        # material only — the logo's colors on the front are untouched.
        plate = {"id": "plate", "type": "shape", "shapeType": "rect",
                 "width": 20, "height": 10, "material": "blue",
                 "transform": {"x": 30, "y": 20},
                 "relief": {"mode": "flush", "depth": 0.6}}
        ol = {**self.OUTLINE, "colorDepth": 0.6}
        v_plain = compile_document(_doc(ol))[0].volumes["red"].volume()
        v_back = compile_document(_doc(ol, back=[plate]))[0].volumes["red"].volume()
        assert v_back == pytest.approx(v_plain, rel=1e-6)
