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
        # back is the bed face — flush inlay (not emboss)
        back=[square("b", 10, 10, 6, "text", {"mode": "flush", "depth": 0.3})])
    scene, _ = compile_document(doc)
    return doc, scene


def parse_3mf(data: bytes):
    with zipfile.ZipFile(BytesIO(data)) as zf:
        assert set(zf.namelist()) == {
            "[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model",
            "Metadata/model_settings.config"}
        return ET.fromstring(zf.read("3D/3dmodel.model"))


class Test3MF:
    def test_one_mesh_object_per_part_plus_assembly(self):
        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        objects = root.findall(f".//{NS}object")
        mesh_objects = [o for o in objects if o.find(f"{NS}mesh") is not None]
        assert len(mesh_objects) == 4  # base + features e, f, b
        assert len(objects) == 5  # + the component assembly
        names = [o.get("name") for o in mesh_objects]
        assert names[0].startswith("base")
        assert [n.split()[0] for n in names[1:]] == ["e", "f", "b"]

    def test_basematerials_colors_match_palette(self):
        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        bases = root.findall(f".//{NS}base")
        colors = {b.get("name"): b.get("displaycolor") for b in bases}
        assert colors == {"Base": "#1A1A1A", "Text": "#FFFFFF", "Accent": "#D4AF37"}

    def test_parts_reference_their_material_index(self):
        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        # basematerials order: base, text, accent (palette order)
        expected = {"base": "0", "e": "1", "f": "2", "b": "1"}
        mesh_objects = [o for o in root.findall(f".//{NS}object")
                        if o.find(f"{NS}mesh") is not None]
        for obj in mesh_objects:
            part = obj.get("name").split()[0]
            assert obj.get("pid") == "1"
            assert obj.get("pindex") == expected[part]

    def test_mesh_counts_match_manifold(self):
        doc, scene = compiled()
        vols = normalized_volumes(scene)
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        from cardforge.export.threemf import normalized_parts
        by_part = {p.id: p.solid for p in normalized_parts(scene)}
        for obj in root.findall(f".//{NS}object"):
            if obj.find(f"{NS}mesh") is None:
                continue
            pid = obj.get("name").split()[0]
            tris = obj.findall(f".//{NS}triangle")
            assert len(tris) == by_part[pid].num_tri()
        # sanity: parts of one material triangulate its full volume
        assert sum(by_part[p].num_tri() for p in ("e", "b")) \
            == sum(v.num_tri() for m, v in vols.items() if m == "text")

    def test_bed_normalization_rests_on_bed(self):
        doc, scene = compiled()
        # valid docs never dip below the bed plane (back emboss is rejected)
        assert min(v.bounding_box()[2] for v in scene.non_empty().values()) >= -1e-9
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

    def test_single_build_item_references_assembly(self):
        """One build item → slicers import one grouped object, not N loose ones."""
        doc, scene = compiled()
        root = parse_3mf(scene_to_3mf(scene, doc.materials))
        items = root.findall(f".//{NS}item")
        assert len(items) == 1
        assembly = next(o for o in root.findall(f".//{NS}object")
                        if o.find(f"{NS}components") is not None)
        assert items[0].get("objectid") == assembly.get("id")
        mesh_ids = {o.get("id") for o in root.findall(f".//{NS}object")
                    if o.find(f"{NS}mesh") is not None}
        comp_refs = {c.get("objectid")
                     for c in assembly.findall(f"{NS}components/{NS}component")}
        assert comp_refs == mesh_ids

    def test_model_settings_maps_parts_to_slots(self):
        """Bambu/Orca read Metadata/model_settings.config to auto-assign a
        filament (extruder = material slot) to every part."""
        doc, scene = compiled()
        data = scene_to_3mf(scene, doc.materials)
        with zipfile.ZipFile(BytesIO(data)) as zf:
            cfg = ET.fromstring(zf.read("Metadata/model_settings.config"))
        model = parse_3mf(data)
        assembly = next(o for o in model.findall(f".//{NS}object")
                        if o.find(f"{NS}components") is not None)
        obj_cfg = cfg.find("object")
        assert obj_cfg.get("id") == assembly.get("id")
        extruders = {}
        for part in obj_cfg.findall("part"):
            meta = {m.get("key"): m.get("value") for m in part.findall("metadata")}
            extruders[meta["name"].split()[0]] = meta["extruder"]
        # slots: base=1, text=2, accent=3 (from the palette)
        assert extruders == {"base": "1", "e": "2", "f": "3", "b": "2"}
        # every mesh object is covered
        part_ids = {p.get("id") for p in obj_cfg.findall("part")}
        mesh_ids = {o.get("id") for o in model.findall(f".//{NS}object")
                    if o.find(f"{NS}mesh") is not None}
        assert part_ids == mesh_ids


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
