"""Golden tests for the compile algorithm — the fidelity contract.

Invariant-based (not absolute snapshots) so they hold across systems with
different font libraries. Shape features give exact analytic volumes.
"""

import json
import math
from pathlib import Path

import pytest

from cardforge.document.migrate import migrate_v1_to_v2
from cardforge.document.schema_v2 import DocumentV2
from cardforge.document.variables import resolve_variables
from cardforge.kernel.compile import compile_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES = sorted((PROJECT_ROOT / "examples").rglob("*.cardforge.json"))

W, H, T = 60.0, 40.0, 2.0
RECT_AREA = W * H  # plain rect outline → exact analytic base volume


def make_doc(front=(), back=(), materials=None, thickness=T):
    mats = materials or [
        {"id": "base", "name": "Base", "color": "#1a1a1a", "role": "base", "slot": 1},
        {"id": "text", "name": "Text", "color": "#ffffff", "role": "text", "slot": 2},
        {"id": "accent", "name": "Accent", "color": "#d4af37", "role": "accent", "slot": 3},
    ]
    return DocumentV2.from_dict({
        "cardforge": "2.0",
        "meta": {"id": "t", "name": "T"},
        "object": {"outline": {"type": "rect", "width": W, "height": H},
                   "thickness": thickness},
        "materials": mats,
        "faces": {"front": {"features": list(front)},
                  "back": {"features": list(back)}},
    })


def square(fid, x, y, size, material, relief, z_order=0):
    return {"id": fid, "type": "shape", "shapeType": "rect",
            "width": size, "height": size,
            "transform": {"x": x, "y": y}, "material": material,
            "relief": relief, "zOrder": z_order}


def volumes_of(doc):
    scene, trace = compile_document(doc)
    return scene, trace, {m: v for m, v in scene.volumes.items() if not v.is_empty()}


def assert_disjoint(scene):
    mats = [m for m, v in scene.volumes.items() if not v.is_empty()]
    for i, a in enumerate(mats):
        for b in mats[i + 1:]:
            inter = (scene.volumes[a] ^ scene.volumes[b]).volume()
            assert inter < 1e-6, f"volumes {a} and {b} overlap by {inter}"


class TestBase:
    def test_base_only_volume_analytic(self):
        scene, _, vols = volumes_of(make_doc())
        assert list(vols) == ["base"]
        assert vols["base"].volume() == pytest.approx(RECT_AREA * T, rel=1e-6)

    def test_base_z_range(self):
        scene, _, vols = volumes_of(make_doc())
        bb = vols["base"].bounding_box()
        assert (bb[2], bb[5]) == pytest.approx((0.0, T))


class TestEmboss:
    def test_emboss_adds_exact_volume_on_surface(self):
        doc = make_doc(front=[square("e", 10, 10, 10, "text",
                                     {"mode": "emboss", "height": 0.5})])
        scene, _, vols = volumes_of(doc)
        assert vols["text"].volume() == pytest.approx(100 * 0.5, rel=1e-6)
        bb = vols["text"].bounding_box()
        assert (bb[2], bb[5]) == pytest.approx((T, T + 0.5)), \
            "emboss must start exactly at z == thickness"
        assert vols["base"].volume() == pytest.approx(RECT_AREA * T, rel=1e-6), \
            "emboss must not carve the base"
        assert_disjoint(scene)


class TestDeboss:
    def test_deboss_carves_base(self):
        doc = make_doc(front=[square("d", 10, 10, 10, "base",
                                     {"mode": "deboss", "depth": 0.3})])
        scene, _, vols = volumes_of(doc)
        assert vols["base"].volume() == pytest.approx(RECT_AREA * T - 100 * 0.3, rel=1e-6)
        assert "text" not in vols and "accent" not in vols

    def test_deboss_recess_depth_via_ray(self):
        doc = make_doc(front=[square("d", 10, 10, 10, "base",
                                     {"mode": "deboss", "depth": 0.3})])
        scene, _, vols = volumes_of(doc)
        # column through cavity: solid z ∈ [0, T−0.3] → volume of a thin
        # column region proves the recess depth
        from manifold3d import CrossSection, FillRule
        probe = CrossSection([[(14, H - 14), (16, H - 14), (16, H - 12), (14, H - 12)]],
                             fillrule=FillRule.EvenOdd).extrude(10).translate((0, 0, -5))
        col = vols["base"] ^ probe
        assert col.volume() == pytest.approx(4 * (T - 0.3), rel=1e-6)


class TestFlushInlay:
    def test_flush_conserves_total_volume(self):
        doc = make_doc(front=[square("f", 20, 15, 8, "accent",
                                     {"mode": "flush", "depth": 0.4})])
        scene, _, vols = volumes_of(doc)
        assert vols["accent"].volume() == pytest.approx(64 * 0.4, rel=1e-6)
        assert vols["base"].volume() == pytest.approx(RECT_AREA * T - 64 * 0.4, rel=1e-6)
        total = sum(v.volume() for v in vols.values())
        assert total == pytest.approx(RECT_AREA * T, rel=1e-6), \
            "flush inlay conserves the object volume"
        # inlay top must be coplanar with the surface
        bb = vols["accent"].bounding_box()
        assert (bb[2], bb[5]) == pytest.approx((T - 0.4, T))
        assert_disjoint(scene)


class TestCut:
    def test_cut_pierces_everything(self):
        doc = make_doc(
            front=[
                square("e", 8, 8, 20, "text", {"mode": "emboss", "height": 0.6}),
                square("c", 10, 10, 5, "base", {"mode": "cut"}, z_order=5),
            ])
        scene, _, vols = volumes_of(doc)
        # base loses a 5×5 column over full thickness
        assert vols["base"].volume() == pytest.approx(RECT_AREA * T - 25 * T, rel=1e-6)
        # the emboss overlapping the hole loses the same column too
        assert vols["text"].volume() == pytest.approx((400 - 25) * 0.6, rel=1e-6)
        assert_disjoint(scene)


class TestDebossBacked:
    def test_floor_plug_geometry(self):
        doc = make_doc(front=[square("db", 10, 10, 10, "base", {
            "mode": "deboss-backed", "depth": 0.6,
            "floorMaterial": "accent", "floorThickness": 0.2})])
        scene, _, vols = volumes_of(doc)
        assert vols["base"].volume() == pytest.approx(RECT_AREA * T - 100 * 0.6, rel=1e-6)
        assert vols["accent"].volume() == pytest.approx(100 * 0.2, rel=1e-6)
        bb = vols["accent"].bounding_box()
        assert (bb[2], bb[5]) == pytest.approx((T - 0.6, T - 0.4)), \
            "floor plug sits at the cavity floor, leaving a 0.4mm recess"
        assert_disjoint(scene)


class TestBackFace:
    def test_back_emboss_rejected_bed_stays_flat(self):
        """Emboss on the bed-facing face must emit NO geometry (it would
        protrude below the bed). The card stays a flat base."""
        doc = make_doc(back=[square("b", 10, 10, 10, "text",
                                    {"mode": "emboss", "height": 0.5})])
        scene, trace, vols = volumes_of(doc)
        assert "text" not in vols, "back emboss must not produce geometry"
        assert vols["base"].volume() == pytest.approx(RECT_AREA * T, rel=1e-6)
        # nothing below the bed plane
        assert vols["base"].bounding_box()[2] == pytest.approx(0.0)
        assert any("emboss is not allowed" in w for w in trace.warnings)

    def test_bed_face_flat_no_geometry_below_zero(self):
        """Whatever back features are used, no volume may dip below z=0."""
        doc = make_doc(back=[
            square("d", 8, 8, 8, "base", {"mode": "deboss", "depth": 0.3}),
            square("f", 20, 8, 8, "accent", {"mode": "flush", "depth": 0.4}),
        ])
        scene, _, vols = volumes_of(doc)
        for mat, v in vols.items():
            assert v.bounding_box()[2] >= -1e-9, f"{mat} dips below the bed"

    def test_back_deboss_carves_bottom(self):
        doc = make_doc(back=[square("bd", 10, 10, 10, "base",
                                    {"mode": "deboss", "depth": 0.3})])
        scene, _, vols = volumes_of(doc)
        from manifold3d import CrossSection, FillRule
        # probe column inside the mirrored cavity footprint
        cx = W - 15  # mirrored center of the 10..20 span
        probe = CrossSection([[(cx - 1, H - 16), (cx + 1, H - 16),
                               (cx + 1, H - 14), (cx - 1, H - 14)]],
                             fillrule=FillRule.EvenOdd).extrude(10).translate((0, 0, -5))
        col = vols["base"] ^ probe
        # cavity at the bottom: solid z ∈ [0.3, T]
        assert col.volume() == pytest.approx(4 * (T - 0.3), rel=1e-6)
        bb = col.bounding_box()
        assert bb[2] == pytest.approx(0.3)


class TestOverlapPolicy:
    def test_later_z_order_wins(self):
        doc = make_doc(front=[
            square("a", 10, 10, 10, "text", {"mode": "flush", "depth": 0.4}, z_order=1),
            square("b", 15, 10, 10, "accent", {"mode": "flush", "depth": 0.4}, z_order=2),
        ])
        scene, _, vols = volumes_of(doc)
        # b keeps its full 100mm² footprint; a loses the 5×10 overlap
        assert vols["accent"].volume() == pytest.approx(100 * 0.4, rel=1e-6)
        assert vols["text"].volume() == pytest.approx(50 * 0.4, rel=1e-6)
        assert_disjoint(scene)


class TestMulticolorIcon:
    SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10">'
           '<rect width="10" height="10" fill="#ff0000"/>'
           '<rect x="10" width="10" height="10" fill="#00ff00"/></svg>')

    def test_each_color_maps_to_material(self):
        doc = make_doc(front=[{
            "id": "i", "type": "icon", "transform": {"x": 20, "y": 15},
            "material": "text", "relief": {"mode": "emboss", "height": 0.4},
            "width": 20, "svgInline": self.SVG,
            "colorMap": {"#ff0000": "accent"},  # green falls back to feature material
        }])
        scene, _, vols = volumes_of(doc)
        assert vols["accent"].volume() == pytest.approx(100 * 0.4, rel=0.02)
        assert vols["text"].volume() == pytest.approx(100 * 0.4, rel=0.02)
        assert_disjoint(scene)


class TestClipping:
    def test_feature_clipped_to_outline(self):
        # square hanging half outside the object
        doc = make_doc(front=[square("e", W - 5, 10, 10, "text",
                                     {"mode": "emboss", "height": 0.5})])
        scene, _, vols = volumes_of(doc)
        assert vols["text"].volume() == pytest.approx(50 * 0.5, rel=1e-6), \
            "geometry outside the outline must be clipped away"


class TestMigratedExamples:
    """Every shipped v1 example must compile into a valid disjoint partition."""

    @pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
    def test_example_compiles_disjoint(self, path):
        data = json.loads(path.read_text())
        doc = DocumentV2.from_dict(resolve_variables(migrate_v1_to_v2(data)))
        scene, trace = compile_document(doc, asset_root=PROJECT_ROOT)
        vols = scene.non_empty()
        assert vols, "compilation must produce geometry"
        assert "base" in vols
        assert_disjoint(scene)
        # nothing silently dropped
        total_features = sum(len(f.features) for f in doc.faces.values())
        assert len(trace.records) + len(trace.skipped) == total_features
