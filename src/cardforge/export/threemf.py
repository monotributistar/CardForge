"""3MF writer — CompiledScene + material palette → .3mf bytes.

The fidelity guarantee lives here: the Studio 3D preview loads the exact
bytes this module produces, and the same bytes are what the user saves and
slices. One 3MF object per non-empty material, colored via core-spec
<basematerials> (readable by Three.js 3MFLoader, Bambu, Orca, Cura).
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from manifold3d import Manifold

from cardforge.document.schema_v2 import Material
from cardforge.kernel.types import CompiledScene

NS_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def mesh_arrays(m: Manifold) -> Tuple[list, list]:
    """Shared-vertex arrays from a Manifold: ([x,y,z]…, [a,b,c]…)."""
    mesh = m.to_mesh()
    verts = [(float(v[0]), float(v[1]), float(v[2])) for v in mesh.vert_properties]
    tris = [(int(t[0]), int(t[1]), int(t[2])) for t in mesh.tri_verts]
    return verts, tris


def normalized_volumes(scene: CompiledScene) -> Dict[str, Manifold]:
    """Non-empty volumes translated so the object rests on z=0 (the bed).

    Back-face emboss extends below z=0 in kernel space; slicers expect the
    model sitting on the platform.
    """
    vols = scene.non_empty()
    if not vols:
        return {}
    min_z = min(v.bounding_box()[2] for v in vols.values())
    if abs(min_z) < 1e-9:
        return vols
    return {m: v.translate((0, 0, -min_z)) for m, v in vols.items()}


def scene_to_3mf(scene: CompiledScene, materials: List[Material],
                 title: str = "CardForge") -> bytes:
    """Serialize the compiled scene as a multi-material 3MF."""
    from xml.etree import ElementTree as ET

    vols = normalized_volumes(scene)
    by_id = {m.id: m for m in materials}
    ordered = [mid for mid in scene.material_order if mid in vols]

    model = ET.Element("model", {"unit": "millimeter", "xmlns": NS_CORE})
    meta_title = ET.SubElement(model, "metadata", {"name": "Title"})
    meta_title.text = title
    meta_app = ET.SubElement(model, "metadata", {"name": "Application"})
    meta_app.text = "CardForge"
    resources = ET.SubElement(model, "resources")
    build = ET.SubElement(model, "build")

    bm = ET.SubElement(resources, "basematerials", {"id": "1"})
    for mid in ordered:
        mat = by_id.get(mid)
        ET.SubElement(bm, "base", {
            "name": (mat.name if mat else mid),
            "displaycolor": (mat.color if mat else "#808080").upper(),
        })

    for idx, mid in enumerate(ordered):
        mat = by_id.get(mid)
        obj = ET.SubElement(resources, "object", {
            "id": str(idx + 2),
            "type": "model",
            "name": f"{mid}" + (f" (slot {mat.slot})" if mat and mat.slot else ""),
            "pid": "1",
            "pindex": str(idx),
        })
        mesh_el = ET.SubElement(obj, "mesh")
        verts_el = ET.SubElement(mesh_el, "vertices")
        tris_el = ET.SubElement(mesh_el, "triangles")
        verts, tris = mesh_arrays(vols[mid])
        for x, y, z in verts:
            ET.SubElement(verts_el, "vertex",
                          {"x": f"{x:.6f}", "y": f"{y:.6f}", "z": f"{z:.6f}"})
        for a, b, c in tris:
            ET.SubElement(tris_el, "triangle",
                          {"v1": str(a), "v2": str(b), "v3": str(c)})
        ET.SubElement(build, "item", {"objectid": str(idx + 2)})

    content_types = ET.Element("Types", {"xmlns": NS_CT})
    ET.SubElement(content_types, "Default", {
        "Extension": "rels",
        "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(content_types, "Default", {
        "Extension": "model",
        "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"})

    rels = ET.Element("Relationships", {"xmlns": NS_REL})
    ET.SubElement(rels, "Relationship", {
        "Target": "/3D/3dmodel.model", "Id": "rel-1",
        "Type": "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"})

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml",
                    ET.tostring(content_types, xml_declaration=True, encoding="unicode"))
        zf.writestr("_rels/.rels",
                    ET.tostring(rels, xml_declaration=True, encoding="unicode"))
        zf.writestr("3D/3dmodel.model",
                    ET.tostring(model, xml_declaration=True, encoding="unicode"))
    return buf.getvalue()
