"""Tests for advanced base: per-corner outline, circle, lattice fill, backing."""

import math

import pytest
from manifold3d import CrossSection, FillRule

from cardforge.document.schema_v2 import DocumentV2
from cardforge.kernel.base import base_region
from cardforge.kernel.compile import compile_document
from cardforge.kernel.features import outline_cross_section

W, H, T = 60.0, 40.0, 2.0


def doc(outline=None, fill=None, features=(), thickness=T):
    d = {
        "cardforge": "2.0", "meta": {"id": "t", "name": "T"},
        "object": {"outline": outline or {"type": "rect", "width": W, "height": H},
                   "thickness": thickness},
        "materials": [
            {"id": "base", "name": "B", "color": "#111111", "role": "base"},
            {"id": "text", "name": "T", "color": "#ffffff", "role": "text"},
        ],
        "faces": {"front": {"features": list(features)}},
    }
    if fill:
        d["object"]["fill"] = fill
    return DocumentV2.from_dict(d)


def emboss_sq(fid="e", x=10, y=10, size=10, backing=None):
    f = {"id": fid, "type": "shape", "shapeType": "rect",
         "width": size, "height": size, "transform": {"x": x, "y": y},
         "material": "text", "relief": {"mode": "emboss", "height": 0.5}}
    if backing is not None:
        f["backing"] = backing
    return f


def probe_column(volume, cx, cy, half=3):
    """Solid volume of `volume` inside a small physical-space column."""
    p = CrossSection([[(cx - half, cy - half), (cx + half, cy - half),
                       (cx + half, cy + half), (cx - half, cy + half)]],
                     fillrule=FillRule.EvenOdd).extrude(10).translate((0, 0, -5))
    return (volume ^ p).volume()


class TestOutlines:
    def test_per_corner_radius(self):
        # 3 curved corners + 1 square (tr sharp)
        cs = outline_cross_section(doc(outline={
            "type": "rounded-rect", "width": W, "height": H, "radius": 5,
            "corners": {"tl": 5, "tr": 0, "br": 5, "bl": 5}}))
        # the tr-sharp variant has more area than an all-rounded rect
        all_round = outline_cross_section(doc(outline={
            "type": "rounded-rect", "width": W, "height": H, "radius": 5}))
        assert cs.area() > all_round.area()
        # top-right point must actually be present (square corner)
        assert any(abs(x - W) < 1e-6 and abs(y - H) < 1e-6
                   for x, y in cs.to_polygons()[0])

    def test_circle_outline(self):
        cs = outline_cross_section(doc(outline={"type": "circle", "diameter": 40}))
        assert cs.area() == pytest.approx(math.pi * 400, rel=0.01)


class TestLattice:
    def test_lattice_is_open_grid(self):
        solid = base_region(doc()).area()
        lat = base_region(doc(fill={"type": "lattice", "pattern": "grid",
                                    "spacing": 5, "lineWidth": 1.2, "border": 2.5})).area()
        assert lat < solid * 0.8, "lattice must be lighter than solid"
        assert lat > 0

    def test_lattice_has_solid_rim(self):
        cs = base_region(doc(fill={"type": "lattice", "pattern": "grid",
                                   "spacing": 6, "lineWidth": 1, "border": 3}))
        # a point on the perimeter band is solid; deep interior between lines is not
        rim_pt = CrossSection.square((1, 1)).translate((W - 1.5, H / 2 - 0.5))
        assert not (cs ^ rim_pt).is_empty(), "perimeter rim must be solid"

    def test_lattice_base_volume(self):
        d = doc(fill={"type": "lattice", "pattern": "grid", "spacing": 5,
                      "lineWidth": 1.2, "border": 2.5})
        scene, _ = compile_document(d)
        assert scene.volumes["base"].volume() < W * H * T * 0.8


class TestBacking:
    LAT = {"type": "lattice", "pattern": "grid", "spacing": 5, "lineWidth": 1.2, "border": 2.5}

    def test_solid_base_no_pad(self):
        scene, _ = compile_document(doc(features=[emboss_sq()]))
        # base is full solid; no extra pad material beyond the slab
        assert scene.volumes["base"].volume() == pytest.approx(W * H * T, rel=1e-6)

    def test_auto_pad_over_lattice(self):
        scene, _ = compile_document(doc(fill=self.LAT, features=[emboss_sq(x=10, y=10, size=10)]))
        # footprint doc (10..20, 10..20) → physical (10..20, H-20..H-10 = 20..30)
        col = probe_column(scene.volumes["base"], 15, 25)
        assert col == pytest.approx(6 * 6 * T, rel=1e-6), "full-thickness pad under feature"

    def test_backing_off_leaves_lattice(self):
        scene, _ = compile_document(doc(fill=self.LAT,
                                        features=[emboss_sq(backing={"mode": "off"})]))
        col = probe_column(scene.volumes["base"], 15, 25)
        assert col < 6 * 6 * T * 0.8, "no pad → only grid under the feature"

    def test_backing_on_forces_pad_on_solid(self):
        # 'on' adds a pad even on a solid base (redundant but explicit) — still valid
        scene, _ = compile_document(doc(features=[emboss_sq(backing={"mode": "on"})]))
        assert scene.volumes["base"].volume() == pytest.approx(W * H * T, rel=1e-6)

    def test_pad_material_override(self):
        scene, _ = compile_document(doc(fill=self.LAT, features=[emboss_sq(
            backing={"mode": "on", "material": "text", "thickness": 0.8})]))
        # a text-material pad plate appears under the feature footprint
        col = probe_column(scene.volumes["text"], 15, 25)
        assert col > 0
        # disjoint
        inter = (scene.volumes["base"] ^ scene.volumes["text"]).volume()
        assert inter < 1e-6

    def test_bed_stays_flat_with_lattice_and_pads(self):
        scene, _ = compile_document(doc(fill=self.LAT, features=[emboss_sq()]))
        for v in scene.non_empty().values():
            assert v.bounding_box()[2] >= -1e-9
