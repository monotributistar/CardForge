"""Golden tests for the compile algorithm — the fidelity contract.

Invariant-based (not absolute snapshots) so they hold across systems with
different font libraries. Shape features give exact analytic volumes.
"""

import json
import math
from pathlib import Path

import pytest
from manifold3d import Manifold

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

    def test_emboss_seated_on_base_no_gap(self):
        """The assembly must be one connected solid: emboss letters sit ON the
        base surface with real contact — a gap would print floating in air."""
        doc = make_doc(
            front=[square("e", 10, 10, 10, "text", {"mode": "emboss", "height": 0.5})],
            back=[square("b", 12, 12, 6, "text", {"mode": "flush", "depth": 0.3})])
        scene, _, vols = volumes_of(doc)
        union = vols["base"] + vols["text"]
        assert len(union.decompose()) == 1, "a part is floating off the base"
        # contact is real, not just bbox-adjacent: sinking the adds by 1µm
        # must create overlap with the base
        sunk = vols["text"].translate((0, 0, -0.001))
        assert (sunk ^ vols["base"]).volume() > 0


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


class TestBackingPlate:
    def test_backing_is_a_visible_plate_not_the_glyph_shape(self):
        """The pad must cover the feature's bounds (+padding) as a plate —
        a pad shaped like the feature itself hides behind it (invisible)."""
        doc = make_doc(back=[dict(
            square("q", 20, 10, 10, "text", {"mode": "flush", "depth": 0.4}),
            backing={"mode": "on", "material": "accent",
                     "thickness": 0.8, "padding": 2},
        )])
        scene, _, vols = volumes_of(doc)
        pad = next(p for p in scene.non_empty_parts() if p.id == "q-pad")
        bb = pad.solid.bounding_box()
        # plate spans the feature bounds + 2mm padding on each side
        assert bb[3] - bb[0] == pytest.approx(14, abs=1e-6)
        assert bb[4] - bb[1] == pytest.approx(14, abs=1e-6)
        # sits on the bed face and is visible from below OUTSIDE the feature:
        # plate area (14x14) minus the feature (10x10) exists at z=0
        assert (bb[2], bb[5]) == pytest.approx((0.0, 0.8))
        assert pad.solid.volume() == pytest.approx(14 * 14 * 0.8 - 10 * 10 * 0.4, rel=1e-6)
        assert_disjoint(scene)

    def test_qr_backing_defaults_padding_to_quiet_zone(self):
        doc = make_doc(back=[{
            "id": "qr", "type": "qr", "qrType": "url",
            "fields": {"url": "https://example.com"}, "size": 20,
            "transform": {"x": 20, "y": 10}, "material": "text",
            "relief": {"mode": "flush", "depth": 0.4},
            "backing": {"mode": "on", "material": "accent", "thickness": 0.8},
        }])
        scene, _, vols = volumes_of(doc)
        pad = next(p for p in scene.non_empty_parts() if p.id == "qr-pad")
        qr = next(p for p in scene.non_empty_parts() if p.id == "qr")
        pb, qb = pad.solid.bounding_box(), qr.solid.bounding_box()
        # plate extends ~quiet zone (2mm default) beyond the modules
        assert qb[0] - pb[0] == pytest.approx(2.0, abs=1e-6)
        assert pb[3] - qb[3] == pytest.approx(2.0, abs=1e-6)
        assert_disjoint(scene)


class TestBackingCrossFace:
    """zOrder is a per-face layer order: a front feature's backing must
    never claim space from the back face, whatever the zOrder values."""

    QR = {"id": "qr", "type": "qr", "qrType": "url",
          "fields": {"url": "https://example.com"}, "size": 10,
          "material": "text", "transform": {"x": 25, "y": 5}, "zOrder": 1,
          "relief": {"mode": "flush", "depth": 0.4}}

    def _doc(self, front_z, backing):
        # front square at x=5..15 — the back QR at x=25..35 mirrors to the
        # same XY region, so their footprints collide through the card.
        return make_doc(
            front=[dict(square("sq", 5, 5, 10, "text",
                               {"mode": "emboss", "height": 0.4},
                               z_order=front_z),
                        backing=backing)],
            back=[self.QR])

    def _qr_volume(self, scene):
        return next(p.solid.volume() for p in scene.non_empty_parts()
                    if p.id == "qr")

    def test_pad_never_swallows_opposite_face(self):
        ref, _, _ = volumes_of(self._doc(1, {"mode": "off"}))
        for front_z in (-5, 1, 5):
            scene, _, _ = volumes_of(
                self._doc(front_z, {"mode": "on", "material": "accent"}))
            assert self._qr_volume(scene) == pytest.approx(
                self._qr_volume(ref), rel=1e-6), \
                f"front zOrder={front_z} backing ate the back QR"
            assert_disjoint(scene)

    def test_default_pad_is_a_plate_on_solid_base(self):
        """Over a solid base an unbounded pad would show through on the
        opposite face — the default must be a thin plate at the surface."""
        scene, _, _ = volumes_of(
            self._doc(1, {"mode": "on", "material": "accent"}))
        pad = next(p.solid for p in scene.non_empty_parts() if p.id == "sq-pad")
        bb = pad.bounding_box()
        assert bb[2] > 0.5, "pad must not reach the back surface"
        assert bb[5] == pytest.approx(T, abs=1e-6)

    def test_explicit_thickness_still_wins(self):
        scene, _, _ = volumes_of(self._doc(
            1, {"mode": "on", "material": "accent", "thickness": 1.0}))
        pad = next(p.solid for p in scene.non_empty_parts() if p.id == "sq-pad")
        bb = pad.bounding_box()
        assert bb[5] - bb[2] == pytest.approx(1.0, abs=1e-6)


class TestBackingPlateShapeAndColumn:
    """Circle plates, and the plaque column claim: the plate ring is the
    feature's quiet zone — lower layers must not emboss on top of it nor
    hollow the base under it."""

    def _doc(self, backing, invader=None):
        front = [dict(square("sq", 10, 10, 10, "text",
                             {"mode": "emboss", "height": 0.4}, z_order=5),
                      backing=backing)]
        if invader:
            front.append(invader)
        return make_doc(front=front)

    def test_circle_plate(self):
        import math
        scene, _, _ = volumes_of(self._doc(
            {"mode": "on", "material": "accent", "shape": "circle",
             "thickness": 0.6, "padding": 2}))
        pad = next(p.solid for p in scene.non_empty_parts() if p.id == "sq-pad")
        bb = pad.bounding_box()
        dia = 10 + 2 * 2  # larger bounds side + 2*padding
        assert bb[3] - bb[0] == pytest.approx(dia, abs=0.05)
        assert bb[4] - bb[1] == pytest.approx(dia, abs=0.05)
        assert pad.volume() == pytest.approx(
            math.pi * (dia / 2) ** 2 * 0.6, rel=0.01)

    def test_plaque_ring_blocks_lower_emboss(self):
        """The 'quiet zone' ask: an embossed background must not land ON
        the plaque of a higher-layer feature."""
        invader = square("inv", 0, 0, 40, "accent",
                         {"mode": "emboss", "height": 0.4}, z_order=1)
        scene, _, _ = volumes_of(self._doc(
            {"mode": "on", "material": "accent"}, invader))
        pad = next(p.solid for p in scene.non_empty_parts() if p.id == "sq-pad")
        inv = next(p.solid for p in scene.non_empty_parts() if p.id == "inv")
        pb = pad.bounding_box()
        from manifold3d import CrossSection, FillRule
        col = (CrossSection([[(pb[0], pb[1]), (pb[3], pb[1]),
                              (pb[3], pb[4]), (pb[0], pb[4])]],
                            fillrule=FillRule.EvenOdd)
               .extrude(3 * T).translate((0, 0, -T / 2)))
        assert (inv ^ col).volume() < 1e-6, "emboss landed on the plaque"
        assert_disjoint(scene)

    def test_plaque_protects_base_under_it(self):
        """A lower-layer deep deboss must not hollow the base below the
        plate — the plaque needs solid support."""
        invader = square("inv", 5, 5, 30, "base",
                         {"mode": "deboss", "depth": 1.2}, z_order=1)
        scene, _, _ = volumes_of(self._doc(
            {"mode": "on", "material": "accent"}, invader))
        base = next(p.solid for p in scene.non_empty_parts() if p.id == "base")
        pad = next(p.solid for p in scene.non_empty_parts() if p.id == "sq-pad")
        pb = pad.bounding_box()
        from manifold3d import CrossSection, FillRule
        under = (CrossSection([[(pb[0], pb[1]), (pb[3], pb[1]),
                                (pb[3], pb[4]), (pb[0], pb[4])]],
                              fillrule=FillRule.EvenOdd).extrude(pb[2]))
        assert (base ^ under).volume() == pytest.approx(under.volume(), rel=1e-6), \
            "base was hollowed under the plaque"


class TestQRQuietZoneKeepOut:
    def _doc(self, qr_z):
        return make_doc(back=[
            square("bg", 0, 0, 40, "text", {"mode": "flush", "depth": 0.4}),
            {"id": "qr", "type": "qr", "qrType": "url",
             "fields": {"url": "https://example.com"}, "size": 20, "quietZone": 3,
             "transform": {"x": 15, "y": 8}, "material": "text",
             "relief": {"mode": "flush", "depth": 0.4}, "zOrder": qr_z},
        ])

    def _square_probe(self):
        from manifold3d import CrossSection, FillRule
        # QR full square (size+2qz = 26) at doc (15,8) on the back face:
        # mirrored x' = W - (15..41), y phys = H - (8..34)
        x0, x1 = W - 41, W - 15
        y0, y1 = H - 34, H - 8
        return CrossSection([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]],
                            fillrule=FillRule.EvenOdd).extrude(1.0).translate((0, 0, -0.1))

    def test_higher_qr_clears_its_quiet_zone(self):
        scene, _, _ = volumes_of(self._doc(qr_z=5))
        bg = next(p.solid for p in scene.non_empty_parts() if p.id == "bg")
        assert (bg ^ self._square_probe()).volume() < 1e-6, \
            "lower-priority feature must not invade the QR square"
        assert_disjoint(scene)

    def test_lower_qr_does_not_claim(self):
        scene, _, _ = volumes_of(self._doc(qr_z=-1))
        bg = next(p.solid for p in scene.non_empty_parts() if p.id == "bg")
        assert (bg ^ self._square_probe()).volume() > 1.0, \
            "explicitly layering the QR below must allow overlap"

    def test_plate_is_keepout_for_lower_layers(self):
        """A backing plate must stay clean: lower-priority features lose any
        geometry that would spill onto it (respecting layer order)."""
        def build(caption_z):
            return make_doc(back=[
                square("trama", 0, 0, 40, "text", {"mode": "flush", "depth": 0.4}),
                dict(square("caption", 15, 15, 10, "text",
                            {"mode": "flush", "depth": 0.4}, z_order=caption_z),
                     backing={"mode": "on", "material": "accent",
                              "thickness": 0.8, "padding": 2}),
            ])
        scene, _, _ = volumes_of(build(caption_z=5))
        trama = next(p.solid for p in scene.non_empty_parts() if p.id == "trama")
        pad = next(p.solid for p in scene.non_empty_parts() if p.id == "caption-pad")
        assert (trama ^ pad).volume() < 1e-6
        # plate column: nothing of the trama inside the plate footprint
        probe = pad.bounding_box()
        from manifold3d import CrossSection, FillRule
        col = CrossSection([[(probe[0], probe[1]), (probe[3], probe[1]),
                             (probe[3], probe[4]), (probe[0], probe[4])]],
                           fillrule=FillRule.EvenOdd).extrude(2.0).translate((0, 0, -0.5))
        assert (trama ^ col).volume() < 1e-6, "trama spilled onto the plaque"
        # reversed layers → invasion allowed
        scene2, _, _ = volumes_of(build(caption_z=-5))
        trama2 = next(p.solid for p in scene2.non_empty_parts() if p.id == "trama")
        assert (trama2 ^ col).volume() > 1.0

    def test_non_qr_plate_gets_default_margin(self):
        doc = make_doc(back=[dict(
            square("t", 20, 15, 10, "text", {"mode": "flush", "depth": 0.4}),
            backing={"mode": "on", "material": "accent", "thickness": 0.8},
        )])
        scene, _, _ = volumes_of(doc)
        pad = next(p for p in scene.non_empty_parts() if p.id == "t-pad")
        bb = pad.solid.bounding_box()
        assert bb[3] - bb[0] == pytest.approx(13, abs=1e-6), \
            "plate should add 1.5mm breathing room on each side"


class TestContentKeepOut:
    """text-blocks and icons claim their bounding box: tiled backgrounds
    (text patterns) must not interleave with their glyphs."""

    def _doc(self, text_z):
        return make_doc(back=[
            {"id": "trama", "type": "text-pattern", "text": "CALL ME",
             "transform": {"x": 0, "y": 0}, "material": "text",
             "relief": {"mode": "flush", "depth": 0.4},
             "font": {"family": "Helvetica Neue", "size": 4}, "spacing": 4,
             "zOrder": 0},
            {"id": "cap", "type": "text-block", "lines": ["HOLA MUNDO"],
             "transform": {"x": 15, "y": 15}, "material": "accent",
             "relief": {"mode": "flush", "depth": 0.4},
             "font": {"family": "Helvetica Neue", "size": 5}, "zOrder": text_z},
        ])

    def _bbox_col(self, solid):
        from manifold3d import CrossSection, FillRule
        b = solid.bounding_box()
        return CrossSection([[(b[0], b[1]), (b[3], b[1]), (b[3], b[4]), (b[0], b[4])]],
                            fillrule=FillRule.EvenOdd).extrude(2).translate((0, 0, -0.5))

    def test_text_block_bbox_excludes_lower_layers(self):
        scene, _, _ = volumes_of(self._doc(text_z=1))
        parts = {p.id: p.solid for p in scene.non_empty_parts()}
        inv = (parts["trama"] ^ self._bbox_col(parts["cap"])).volume()
        assert inv < 1e-6, "trama interleaved with the text block glyphs"
        assert_disjoint(scene)

    def test_lower_text_block_does_not_claim(self):
        scene, _, _ = volumes_of(self._doc(text_z=-1))
        parts = {p.id: p.solid for p in scene.non_empty_parts()}
        inv = (parts["trama"] ^ self._bbox_col(parts["cap"])).volume()
        assert inv > 0.5, "explicit layering below must allow overlap"

    def test_adjacent_text_blocks_unclipped(self):
        """Exact-bbox claims: stacked texts with separate boxes never clip
        each other, whatever their layer order."""
        doc = make_doc(front=[
            {"id": "a", "type": "text-block", "lines": ["AAAA"],
             "transform": {"x": 10, "y": 10}, "material": "text",
             "relief": {"mode": "emboss", "height": 0.4},
             "font": {"family": "Helvetica Neue", "size": 5}, "zOrder": 0},
            {"id": "b", "type": "text-block", "lines": ["BBBB"],
             "transform": {"x": 10, "y": 20}, "material": "text",
             "relief": {"mode": "emboss", "height": 0.4},
             "font": {"family": "Helvetica Neue", "size": 5}, "zOrder": 1},
        ])
        scene, _, _ = volumes_of(doc)
        parts = {p.id: p.solid for p in scene.non_empty_parts()}
        va, vb = parts["a"].volume(), parts["b"].volume()
        doc2 = make_doc(front=[{"id": "a", "type": "text-block", "lines": ["AAAA"],
             "transform": {"x": 10, "y": 10}, "material": "text",
             "relief": {"mode": "emboss", "height": 0.4},
             "font": {"family": "Helvetica Neue", "size": 5}}])
        solo = compile_document(doc2)[0].non_empty()["text"].volume()
        assert va == pytest.approx(solo, rel=1e-6), "neighbor clipped text A"


class TestHole:
    """hole feature — through-cuts (keyring circle / lanyard slot) with an
    optional material tab that lets the hole live outside the outline."""

    @staticmethod
    def hole(fid="h", x=10.0, y=10.0, tab=False, hole_type="circle", **kw):
        f = {"id": fid, "type": "hole", "holeType": hole_type,
             "transform": {"x": x, "y": y}, "material": "base",
             "relief": {"mode": "cut"}}
        if tab:
            f["tab"] = True
        f.update(kw)
        return f

    def test_circle_hole_pierces_base(self):
        doc = make_doc(front=[self.hole(diameter=6.0)])
        scene, _, vols = volumes_of(doc)
        # ~π·r²·T removed (polygonal circle → slightly less than π)
        removed = RECT_AREA * T - vols["base"].volume()
        assert removed == pytest.approx(math.pi * 9 * T, rel=0.01)
        assert vols["base"].genus() == 1, "hole must pierce all the way through"

    def test_slot_hole_analytic_area(self):
        # Stadium: (w-h)·h rectangle + full circle of d=h
        w, h = 14.0, 5.0
        doc = make_doc(front=[self.hole(hole_type="slot", width=w, height=h)])
        scene, _, vols = volumes_of(doc)
        removed = RECT_AREA * T - vols["base"].volume()
        stadium = (w - h) * h + math.pi * (h / 2) ** 2
        assert removed == pytest.approx(stadium * T, rel=0.01)

    def test_tab_adds_material_outside_outline(self):
        # Circle d=6 centered ON the right edge (anchor x = W-3 → spans W-3..W+3);
        # tab margin 3 → lug reaches W+6. Base must extend past the outline.
        doc = make_doc(front=[self.hole(x=W - 3, y=10, diameter=6.0,
                                        tab=True, tabMargin=3.0)])
        scene, trace, vols = volumes_of(doc)
        bb = vols["base"].bounding_box()
        assert bb[3] == pytest.approx(W + 6, abs=0.05), \
            "tab lug must extend beyond the outline edge"
        assert vols["base"].genus() == 1, "the lug must carry a real hole"
        assert not any("open notch" in w for w in trace.warnings)
        assert_disjoint(scene)

    def test_hole_outside_without_tab_warns(self):
        doc = make_doc(front=[self.hole(x=W - 3, y=10, diameter=6.0)])
        _, trace, vols = volumes_of(doc)
        assert any("open notch" in w for w in trace.warnings)

    def test_tab_is_solid_over_lattice(self):
        # On a lattice base the lug must still be solid (structural).
        raw = make_doc(front=[self.hole(x=W - 3, y=10, diameter=6.0,
                                        tab=True, tabMargin=3.0)]).to_dict()
        raw["object"]["fill"] = {"type": "lattice", "pattern": "grid",
                                 "spacing": 5, "lineWidth": 1.2, "border": 2.5}
        doc = DocumentV2.from_dict(raw)
        scene, _, vols = volumes_of(doc)
        # Probe a point inside the lug ring (between hole edge and lug edge)
        probe = (vols["base"] ^
                 Manifold.cube((1, 1, T)).translate((W + 3.5, H - 10 - 0.5, 0)))
        assert probe.volume() == pytest.approx(1 * 1 * T, rel=1e-3), \
            "lug region must be solid, not latticed"

    def test_back_face_hole_mirrors(self):
        # Same hole authored on the back face: mirrored around the vertical
        # edge, so doc x=10 (left) lands on physical right.
        front = make_doc(front=[self.hole(x=10, y=10, diameter=6.0)])
        back = make_doc(back=[self.hole(x=10, y=10, diameter=6.0)])
        vf = volumes_of(front)[2]["base"]
        vb = volumes_of(back)[2]["base"]
        assert vf.volume() == pytest.approx(vb.volume(), rel=1e-6)
        mirrored = vf.mirror((1, 0, 0)).translate((W, 0, 0))
        assert (mirrored ^ vb).volume() == pytest.approx(vb.volume(), rel=1e-4), \
            "back-face hole must be the mirror image of the front-face one"

    def test_hole_cuts_through_emboss(self):
        # A hole overlapping an embossed square must pierce the emboss too.
        doc = make_doc(front=[
            square("e", 10, 10, 10, "text", {"mode": "emboss", "height": 0.5}),
            self.hole(x=12, y=12, diameter=4.0),
        ])
        scene, _, vols = volumes_of(doc)
        assert vols["text"].volume() < 100 * 0.5 - 1.0, \
            "cut must remove volume from the emboss"
        assert_disjoint(scene)

    def test_hole_outside_outline_is_not_a_blocking_error(self):
        from cardforge.kernel.constraints import check_constraints
        doc = make_doc(front=[self.hole(x=W - 3, y=10, diameter=6.0,
                                        tab=True, tabMargin=3.0)])
        scene, trace = compile_document(doc)
        issues = check_constraints(doc, trace)
        assert not any(i.code == "outside-bounds" for i in issues), \
            "a tabbed hole outside the outline must not raise outside-bounds"


class TestPocket:
    """pocket feature — a blind cylindrical cavity sized to hold an insert
    (magnet, RFID tag). The bore cut is the insert's nominal size opened up by
    the stated clearances; `ceiling` decides whether it opens at the surface
    or is sealed under a printed lid."""

    PT = 4.0  # thick enough to actually bury a Ø6×2 magnet

    @staticmethod
    def pocket(fid="p", x=20.0, y=15.0, diameter=6.0, depth=2.0, **kw):
        f = {"id": fid, "type": "pocket", "pocketType": "circle",
             "diameter": diameter, "depth": depth,
             "transform": {"x": x, "y": y}, "material": "base",
             "relief": {"mode": "cut"}}
        f.update(kw)
        return f

    def bore_volume(self, diameter, depth):
        return math.pi * (diameter / 2) ** 2 * depth

    def test_open_pocket_carves_the_bore(self):
        # Default fit: Ø6+0.2 bore, 2+0.1 deep.
        doc = make_doc(front=[self.pocket()], thickness=self.PT)
        scene, _, vols = volumes_of(doc)
        removed = RECT_AREA * self.PT - vols["base"].volume()
        assert removed == pytest.approx(self.bore_volume(6.2, 2.1), rel=0.01)
        assert vols["base"].genus() == 0, "an open pocket is a dent, not a hole"

    def test_pocket_leaves_a_floor(self):
        doc = make_doc(front=[self.pocket()], thickness=self.PT)
        _, _, vols = volumes_of(doc)
        # Probe a 1mm cube on the bed directly under the pocket centre.
        probe = vols["base"] ^ Manifold.cube((1, 1, 1)).translate(
            (20 + 3.1 - 0.5, H - 15 - 3.1 - 0.5, 0))
        assert probe.volume() == pytest.approx(1.0, rel=1e-3), \
            "the floor under the pocket must stay solid"

    def test_clearance_opens_the_bore(self):
        tight = make_doc(front=[self.pocket(clearance=0.0, depthClearance=0.0)],
                         thickness=self.PT)
        loose = make_doc(front=[self.pocket(clearance=0.6, depthClearance=0.0)],
                         thickness=self.PT)
        v_tight = RECT_AREA * self.PT - volumes_of(tight)[2]["base"].volume()
        v_loose = RECT_AREA * self.PT - volumes_of(loose)[2]["base"].volume()
        assert v_tight == pytest.approx(self.bore_volume(6.0, 2.0), rel=0.01)
        assert v_loose == pytest.approx(self.bore_volume(6.6, 2.0), rel=0.01)

    def test_ceiling_seals_the_pocket(self):
        doc = make_doc(front=[self.pocket(ceiling=0.8)], thickness=self.PT)
        scene, _, vols = volumes_of(doc)
        base = vols["base"]
        assert base.genus() == -1, "a sealed pocket is an enclosed void"
        # Nothing of it reaches either surface: the full outline is still there.
        bb = base.bounding_box()
        assert (bb[2], bb[5]) == pytest.approx((0.0, self.PT), abs=1e-6)
        # ...and the lid over it is solid material.
        lid = base ^ Manifold.cube((1, 1, 0.8)).translate(
            (20 + 3.1 - 0.5, H - 15 - 3.1 - 0.5, self.PT - 0.8))
        assert lid.volume() == pytest.approx(0.8, rel=1e-3)

    def test_pocket_breaking_through_warns(self):
        doc = make_doc(front=[self.pocket(depth=3.8, ceiling=0.4)],
                       thickness=self.PT)
        _, trace, _ = volumes_of(doc)
        assert any("breaks through" in w for w in trace.warnings)

    def test_back_face_pocket_opens_on_the_bed_face(self):
        doc = make_doc(back=[self.pocket()], thickness=self.PT)
        _, _, vols = volumes_of(doc)
        base = vols["base"]
        # Back-face features mirror around the vertical edge: doc x=20 lands at
        # physical x = W-20-6.2. Probe the bed face there — it must be open...
        cx, cy = W - 20 - 3.1, H - 15 - 3.1
        at_bed = base ^ Manifold.cube((1, 1, 1)).translate((cx - 0.5, cy - 0.5, 0))
        assert at_bed.volume() == pytest.approx(0.0, abs=1e-6)
        # ...and the top face solid.
        at_top = base ^ Manifold.cube((1, 1, 1)).translate(
            (cx - 0.5, cy - 0.5, self.PT - 1))
        assert at_top.volume() == pytest.approx(1.0, rel=1e-3)

    def test_pocket_volume_stays_empty_of_other_materials(self):
        # A flush inlay sunk into the same column must not fill the cavity the
        # insert is meant to occupy — the pocket claims that volume.
        doc = make_doc(front=[
            square("inlay", 18, 13, 12, "text", {"mode": "flush", "depth": 1.0},
                   z_order=0),
            self.pocket(z_order=1),
        ], thickness=self.PT)
        scene, _, vols = volumes_of(doc)
        cavity = Manifold.cylinder(2.1, 3.1, 3.1, circular_segments=64) \
            .translate((20 + 3.1, H - 15 - 3.1, self.PT - 2.1))
        assert (vols["text"] ^ cavity).volume() == pytest.approx(0.0, abs=1e-3)
        assert_disjoint(scene)

    def test_lattice_base_gets_a_solid_collar(self):
        raw = make_doc(front=[self.pocket()], thickness=self.PT).to_dict()
        raw["object"]["fill"] = {"type": "lattice", "pattern": "grid",
                                 "spacing": 5, "lineWidth": 1.2, "border": 2.5}
        doc = DocumentV2.from_dict(raw)
        _, _, vols = volumes_of(doc)
        # Ring between the bore edge (r=3.1) and the collar edge (r=4.6):
        # a 1mm cube centred at r=3.8 from the axis must be solid, not lattice.
        probe = vols["base"] ^ Manifold.cube((1, 1, self.PT)).translate(
            (20 + 3.1 + 3.3, H - 15 - 3.1 - 0.5, 0))
        assert probe.volume() == pytest.approx(self.PT, rel=1e-3), \
            "an insert needs solid material around it, not a grid of air"
