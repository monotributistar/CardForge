"""Tests for the v2 exporters — 3MF structure/colors and STL parity."""

import struct
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

import pytest

from cardforge.export.stl import manifold_to_stl, scene_to_stls
from cardforge.export.threemf import NS_CORE, normalized_volumes, scene_to_3mf
from cardforge.kernel.compile import compile_document

from tests.kernel.test_compile import make_doc, square

NS = f"{{{NS_CORE}}}"


def compiled():
    doc = make_doc(
        front=[square("e", 10, 10, 10, "text", {"mode": "emboss", "height": 0.5}),
               square("f", 30, 15, 8, "accent", {"mode": "flush", "depth": 0.4})],
        back=[square("b", 10, 10, 6, "text", {"mode": "emboss", "height": 0.3})])
    scene, _ = compile_document(doc)
    return doc, scene


def parse_3mf(data: bytes):
    with zipfile.ZipFile(BytesIO(data)) as zf:
        assert set(zf.namelist()) == {
            "[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
        return ET.fromstring(zf.read("3D/3dmodel.model"))


class Test3MF:
    def test_one_object_per_material(self):
        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        objects = root.findall(f".//{NS}object")
        assert len(objects) == 3  # base, text, accent all non-empty
        names = [o.get("name") for o in objects]
        assert names[0].startswith("base")

    def test_basematerials_colors_match_palette(self):
        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        bases = root.findall(f".//{NS}base")
        colors = {b.get("name"): b.get("displaycolor") for b in bases}
        assert colors == {"Base": "#1A1A1A", "Text": "#FFFFFF", "Accent": "#D4AF37"}

    def test_objects_reference_material_index(self):
        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        for i, obj in enumerate(root.findall(f".//{NS}object")):
            assert obj.get("pid") == "1"
            assert obj.get("pindex") == str(i)

    def test_mesh_counts_match_manifold(self):
        doc, scene = compiled()
        vols = normalized_volumes(scene)
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        for obj in root.findall(f".//{NS}object"):
            mid = obj.get("name").split()[0]
            tris = obj.findall(f".//{NS}triangle")
            assert len(tris) == vols[mid].num_tri()

    def test_bed_normalization(self):
        doc, scene = compiled()
        # kernel space: back emboss goes below 0
        assert min(v.bounding_box()[2] for v in scene.non_empty().values()) < 0
        vols = normalized_volumes(scene)
        min_z = min(v.bounding_box()[2] for v in vols.values())
        assert min_z == pytest.approx(0.0, abs=1e-9), "model must rest on the bed"

    def test_manifold_meshes(self):
        """Every exported mesh must be watertight (slicer requirement)."""
        from collections import Counter

        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        for obj in root.findall(f".//{NS}object"):
            edges = Counter()
            for t in obj.findall(f".//{NS}triangle"):
                a, b, c = (int(t.get(k)) for k in ("v1", "v2", "v3"))
                for e in ((a, b), (b, c), (c, a)):
                    edges[tuple(sorted(e))] += 1
            bad = [e for e, n in edges.items() if n != 2]
            assert not bad, f"object {obj.get('name')}: {len(bad)} non-manifold edges"

    def test_build_items_reference_objects(self):
        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        obj_ids = {o.get("id") for o in root.findall(f".//{NS}object")}
        item_refs = {i.get("objectid") for i in root.findall(f".//{NS}item")}
        assert item_refs == obj_ids


class TestSTL:
    def test_stl_volume_parity_with_manifold(self):
        doc, scene = compiled()
        stls = scene_to_stls(scene, doc.materials)
        vols = normalized_volumes(scene)
        for mid, data in stls.items():
            n_tris = struct.unpack("<I", data[80:84])[0]
            assert n_tris == vols[mid].num_tri()
            assert len(data) == 84 + n_tris * 50
            # signed volume from the STL must match the Manifold volume
            vol = 0.0
            off = 84
            for _ in range(n_tris):
                # record = normal (12B) + 3 vertices (36B) + attr (2B)
                v = struct.unpack("<9f", data[off + 12:off + 48])
                a, b, c = v[0:3], v[3:6], v[6:9]
                vol += (a[0] * (b[1] * c[2] - b[2] * c[1])
                        - a[1] * (b[0] * c[2] - b[2] * c[0])
                        + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
                off += 50
            assert vol == pytest.approx(vols[mid].volume(), rel=1e-4)

    def test_stl_per_material(self):
        doc, scene = compiled()
        stls = scene_to_stls(scene, doc.materials)
        assert set(stls) == {"base", "text", "accent"}

    def test_header_carries_slot(self):
        doc, scene = compiled()
        stls = scene_to_stls(scene, doc.materials)
        assert b"slot2" in stls["text"][:80]
