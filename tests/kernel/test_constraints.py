"""Tests for kernel constraint checks (relocated from domain/constraints.py)."""

import pytest

from cardforge.kernel.compile import compile_document
from cardforge.kernel.constraints import check_constraints
from cardforge.kernel.types import Severity

from tests.kernel.test_compile import make_doc, square


def issues_for(doc):
    scene, trace = compile_document(doc)
    return check_constraints(doc, trace)


def codes(issues):
    return [i.code for i in issues]


class TestConstraints:
    def test_clean_document_no_issues(self):
        doc = make_doc(front=[square("ok", 10, 10, 10, "text",
                                     {"mode": "emboss", "height": 0.4})])
        assert issues_for(doc) == []

    def test_outside_bounds_error(self):
        doc = make_doc(front=[square("out", 55, 10, 10, "text",
                                     {"mode": "emboss", "height": 0.4})])
        issues = issues_for(doc)
        assert "outside-bounds" in codes(issues)
        assert issues[codes(issues).index("outside-bounds")].severity == Severity.ERROR

    def test_safe_margin_warning(self):
        doc = make_doc(front=[square("edge", 0.5, 10, 10, "text",
                                     {"mode": "emboss", "height": 0.4})])
        issues = issues_for(doc)
        assert "safe-margin" in codes(issues)

    def test_min_feature_size_error(self):
        doc = make_doc(front=[square("tiny", 10, 10, 0.4, "text",
                                     {"mode": "emboss", "height": 0.4})])
        assert "min-feature-size" in codes(issues_for(doc))

    # QR sizing/contrast/quiet-zone moved to the manufacturing analyzer
    # (nozzle-aware) — see tests/manufacturing/test_qr.py.

    def test_depth_exceeds_thickness_error(self):
        doc = make_doc(front=[square("deep", 10, 10, 10, "base",
                                     {"mode": "deboss", "depth": 2.5})])
        issues = issues_for(doc)
        assert "depth-exceeds-thickness" in codes(issues)

    def test_back_emboss_is_error(self):
        doc = make_doc(back=[square("b", 10, 10, 10, "text",
                                    {"mode": "emboss", "height": 0.4})])
        issues = issues_for(doc)
        assert "back-emboss-not-flat" in codes(issues)
        err = next(i for i in issues if i.code == "back-emboss-not-flat")
        assert err.severity == Severity.ERROR

    def test_overlap_warning(self):
        doc = make_doc(front=[
            square("a", 10, 10, 10, "text", {"mode": "emboss", "height": 0.4}),
            square("b", 15, 12, 10, "accent", {"mode": "emboss", "height": 0.4}),
        ])
        issues = issues_for(doc)
        assert "overlap" in codes(issues)

    def test_full_face_pattern_exempt_from_size_checks(self):
        doc = make_doc(front=[{
            "id": "p", "type": "pattern", "patternType": "dots", "spacing": 4,
            "region": "face", "transform": {"x": 0, "y": 0},
            "material": "base", "relief": {"mode": "deboss", "depth": 0.2},
        }])
        assert "safe-margin" not in codes(issues_for(doc))


TRIANGLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 40">'
    '<path d="M30 2 L58 38 L2 38 Z" fill="#d4af37"/></svg>'
)


class TestOutlineClipping:
    """An SVG silhouette cuts features its bounding box never leaves."""

    @staticmethod
    def _doc(feature, face="front"):
        doc = make_doc(**{face: [feature]})
        doc.object.outline.type = "path"
        doc.object.outline.svg_inline = TRIANGLE_SVG
        return doc

    def test_corner_of_the_bounding_box_is_outside_the_shape(self):
        corner = square("logo", 2, 2, 10, "text", {"mode": "emboss", "height": 0.4})
        assert "clipped-by-outline" in codes(issues_for(self._doc(corner)))

    def test_feature_within_the_silhouette_is_clean(self):
        inside = square("ok", 25, 26, 8, "text", {"mode": "emboss", "height": 0.4})
        assert "clipped-by-outline" not in codes(issues_for(self._doc(inside)))

    def test_a_clipped_qr_is_an_error(self):
        qr = {"id": "qr", "type": "qr", "qrType": "url",
              "fields": {"url": "https://example.com"}, "size": 24,
              "transform": {"x": 2, "y": 2}, "material": "text",
              "relief": {"mode": "flush", "depth": 0.4}}
        err = next(i for i in issues_for(self._doc(qr, face="back"))
                   if i.code == "clipped-by-outline")
        assert err.severity == Severity.ERROR

    def test_a_plain_rect_outline_never_clips(self):
        edge = square("edge", 0, 0, 10, "text", {"mode": "emboss", "height": 0.4})
        assert "clipped-by-outline" not in codes(issues_for(make_doc(front=[edge])))


LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 40">'
    '<rect width="60" height="40" fill="#1a1a1a"/>'
    '<circle cx="30" cy="20" r="12" fill="#d4af37"/></svg>'
)


def logo_doc(back=(), color_depth=0.6, layer_height=0.2, **outline):
    """Card whose shape and front colors come from an SVG logo."""
    doc = make_doc(back=back)
    doc.object.outline.type = "path"
    doc.object.outline.svg_inline = LOGO_SVG
    doc.object.outline.color_map = {"#1a1a1a": "base", "#d4af37": "accent"}
    doc.object.outline.color_depth = color_depth
    doc.manufacturing.layer_height = layer_height
    for k, v in outline.items():
        setattr(doc.object.outline, k, v)
    return doc


class TestColorLayer:
    def test_layer_thinner_than_two_layers_warns(self):
        issues = issues_for(logo_doc(color_depth=0.3, layer_height=0.2))
        assert "color-layer-too-thin" in codes(issues)

    def test_two_layers_is_enough(self):
        assert "color-layer-too-thin" not in codes(
            issues_for(logo_doc(color_depth=0.4, layer_height=0.2)))

    def test_through_colors_are_not_a_layer(self):
        # No colorDepth: the colors run edge to edge, nothing to undercut.
        doc = logo_doc(color_depth=0.0)
        assert "color-layer-too-thin" not in codes(issues_for(doc))

    def test_deep_back_carve_reaches_the_front_colors(self):
        # T=2, colour layer 0.6 → only 1.4mm of base behind the artwork.
        deep = square("deep", 10, 10, 10, "text", {"mode": "flush", "depth": 1.6})
        issues = issues_for(logo_doc(back=[deep]))
        assert "carve-reaches-color-layer" in codes(issues)
        w = next(i for i in issues if i.code == "carve-reaches-color-layer")
        assert w.severity == Severity.WARNING and w.face_id == "back"

    def test_shallow_back_carve_is_fine(self):
        ok = square("ok", 10, 10, 10, "text", {"mode": "flush", "depth": 0.6})
        assert "carve-reaches-color-layer" not in codes(issues_for(logo_doc(back=[ok])))


class TestPocketConstraints:
    """A pocket is sized for a real object, so what the checks watch is the
    material LEFT around it and whether the bore was opened up enough."""

    @staticmethod
    def doc(thickness=4.0, **kw):
        feat = {"id": "p", "type": "pocket", "pocketType": "circle",
                "diameter": 6, "depth": 2, "transform": {"x": 20, "y": 15},
                "material": "base", "relief": {"mode": "cut"}}
        feat.update(kw)
        return make_doc(front=[feat], thickness=thickness)

    def test_healthy_pocket_is_clean(self):
        assert issues_for(self.doc()) == []

    def test_pocket_deeper_than_the_body_is_an_error(self):
        issues = issues_for(self.doc(thickness=2.0))
        assert "pocket-breaks-through" in codes(issues)
        err = next(i for i in issues if i.code == "pocket-breaks-through")
        assert err.severity == Severity.ERROR

    def test_thin_floor_warns(self):
        # 2.1mm cavity in a 2.6mm body → 0.5mm of floor left.
        issues = issues_for(self.doc(thickness=2.6))
        assert "pocket-floor-too-thin" in codes(issues)
        assert "pocket-breaks-through" not in codes(issues)

    def test_sealed_pocket_reports_the_pause_height(self):
        issues = issues_for(self.doc(ceiling=1.0))
        pause = next(i for i in issues if i.code == "pocket-needs-print-pause")
        assert "z = 3.00mm" in pause.message
        assert "pocket-ceiling-too-thin" not in codes(issues)

    def test_back_face_pause_is_measured_from_the_bed(self):
        feat = {"id": "p", "type": "pocket", "pocketType": "circle",
                "diameter": 6, "depth": 2, "ceiling": 1.0,
                "transform": {"x": 20, "y": 15}, "material": "base",
                "relief": {"mode": "cut"}}
        issues = issues_for(make_doc(back=[feat], thickness=4.0))
        pause = next(i for i in issues if i.code == "pocket-needs-print-pause")
        assert "z = 3.10mm" in pause.message

    def test_thin_lid_warns(self):
        issues = issues_for(self.doc(ceiling=0.3))
        assert "pocket-ceiling-too-thin" in codes(issues)

    def test_zero_clearance_warns(self):
        issues = issues_for(self.doc(clearance=0))
        assert "pocket-no-clearance" in codes(issues)

    def test_stated_clearance_is_accepted(self):
        assert "pocket-no-clearance" not in codes(issues_for(self.doc(clearance=0.15)))

    def test_floor_exactly_at_the_minimum_is_accepted(self):
        # The wizard sizes a card to the thinnest body that fits the insert,
        # so the floor lands ON the limit: 3.9 - (3 + 0.1) = 0.8mm. In binary
        # that subtraction is a hair under 0.8 — it must not read as too thin,
        # or every card the wizard builds warns about itself.
        issues = issues_for(self.doc(thickness=3.9, diameter=8, depth=3))
        assert "pocket-floor-too-thin" not in codes(issues)
        assert issues == []
