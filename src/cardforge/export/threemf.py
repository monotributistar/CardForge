"""3MF writer — CompiledScene + material palette → .3mf bytes.

The fidelity guarantee lives here: the Studio 3D preview loads the exact
bytes this module produces, and the same bytes are what the user saves and
slices.

Structure: one mesh object per scene part (the base body + one per feature),
colored via core-spec <basematerials>, all wrapped in a single component
assembly with ONE build item — slicers import one grouped object whose parts
carry the feature names. A Metadata/model_settings.config (BambuStudio/Orca
dialect) maps every part to its material's slot so those slicers assign
filaments automatically; other consumers ignore the extra file.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from manifold3d import Manifold

from cardforge.document.schema_v2 import Material
from cardforge.kernel.types import CompiledScene, ScenePart

NS_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def mesh_arrays(m: Manifold) -> Tuple[list, list]:
    """Shared-vertex arrays from a Manifold: ([x,y,z]…, [a,b,c]…).

    numpy → Python lists in one C call; per-element float()/int() casts cost
    ~100ms on a full card."""
    mesh = m.to_mesh()
    verts = mesh.vert_properties[:, :3].tolist()
    tris = mesh.tri_verts.tolist()
    return verts, tris


def _bed_offset(vols) -> float:
    """z shift that rests the assembly on z=0 (the bed)."""
    if not vols:
        return 0.0
    min_z = min(v.bounding_box()[2] for v in vols)
    return 0.0 if abs(min_z) < 1e-9 else -min_z


def normalized_volumes(scene: CompiledScene) -> Dict[str, Manifold]:
    """Non-empty per-material volumes translated so the object rests on z=0."""
    vols = scene.non_empty()
    dz = _bed_offset(list(vols.values()))
    if dz == 0.0:
        return vols
    return {m: v.translate((0, 0, dz)) for m, v in vols.items()}


def normalized_parts(scene: CompiledScene) -> List[ScenePart]:
    """Non-empty parts translated by the SAME bed offset as the volumes."""
    parts = scene.non_empty_parts()
    dz = _bed_offset([p.solid for p in parts])
    if dz == 0.0:
        return parts
    return [ScenePart(p.id, p.material, p.solid.translate((0, 0, dz)), p.name)
            for p in parts]


def part_label(part: ScenePart, mat: Optional[Material]) -> str:
    """The exact object name written into the 3MF (and matched by the Studio
    viewer to map meshes back to parts)."""
    return ((part.name or part.id)
            + (f" (slot {mat.slot})" if mat and mat.slot else ""))


def _model_settings_config(assembly_id: int, title: str,
                           part_objects: List[Tuple[int, ScenePart]],
                           by_id: Dict[str, Material]) -> str:
    """BambuStudio/OrcaSlicer per-part config: name + extruder per part."""
    from xml.sax.saxutils import quoteattr

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>",
             f'  <object id="{assembly_id}">',
             f'    <metadata key="name" value={quoteattr(title)}/>']
    for obj_id, part in part_objects:
        mat = by_id.get(part.material)
        slot = mat.slot if (mat and mat.slot) else 1
        label = part.name or part.id
        name = f"{label} [{mat.name}]" if mat else label
        lines += [f'    <part id="{obj_id}" subtype="normal_part">',
                  f'      <metadata key="name" value={quoteattr(name)}/>',
                  f'      <metadata key="extruder" value="{slot}"/>',
                  "    </part>"]
    lines += ["  </object>", "</config>", ""]
    return "\n".join(lines)


def scene_to_3mf(scene: CompiledScene, materials: List[Material],
                 title: str = "CardForge") -> bytes:
    """Serialize the compiled scene as a multi-material, multi-part 3MF.

    The model XML is assembled from strings: a full card is ~100k vertex/
    triangle elements, and one ElementTree node per element costs ~1s per
    compile. Only human-supplied text (names/title) needs escaping — all
    other values are numeric."""
    from xml.etree import ElementTree as ET
    from xml.sax.saxutils import escape, quoteattr

    parts = normalized_parts(scene)
    by_id = {m.id: m for m in materials}
    # basematerials in palette order, restricted to materials actually used
    used = {p.material for p in parts}
    mat_ids = [mid for mid in scene.material_order if mid in used]
    mat_index = {mid: i for i, mid in enumerate(mat_ids)}

    out: List[str] = [
        "<?xml version='1.0' encoding='utf-8'?>",
        f'<model unit="millimeter" xmlns="{NS_CORE}">',
        f'<metadata name="Title">{escape(title)}</metadata>',
        '<metadata name="Application">CardForge</metadata>',
        "<resources>",
        '<basematerials id="1">',
    ]
    for mid in mat_ids:
        mat = by_id.get(mid)
        out.append(f'<base name={quoteattr(mat.name if mat else mid)} '
                   f'displaycolor="{(mat.color if mat else "#808080").upper()}"/>')
    out.append("</basematerials>")

    part_objects: List[Tuple[int, ScenePart]] = []
    for idx, part in enumerate(parts):
        obj_id = idx + 2
        part_objects.append((obj_id, part))
        mat = by_id.get(part.material)
        out.append(f'<object id="{obj_id}" type="model" '
                   f'name={quoteattr(part_label(part, mat))} pid="1" '
                   f'pindex="{mat_index[part.material]}">')
        verts, tris = mesh_arrays(part.solid)
        out.append("<mesh><vertices>")
        out.append("".join(
            f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>'
            for x, y, z in verts))
        out.append("</vertices><triangles>")
        out.append("".join(
            f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris))
        out.append("</triangles></mesh></object>")

    # One assembly object referencing every part as a component, and a single
    # build item for it: slicers then load one object with aligned parts
    # instead of N loose objects that trip collision checks.
    assembly_id: Optional[int] = None
    if part_objects:
        assembly_id = len(parts) + 2
        out.append(f'<object id="{assembly_id}" type="model" '
                   f'name={quoteattr(title)}><components>')
        out.extend(f'<component objectid="{obj_id}"/>'
                   for obj_id, _ in part_objects)
        out.append("</components></object>")
    out.append("</resources>")
    out.append("<build>")
    if assembly_id is not None:
        out.append(f'<item objectid="{assembly_id}"/>')
    out.append("</build></model>")
    model_xml = "".join(out)

    content_types = ET.Element("Types", {"xmlns": NS_CT})
    ET.SubElement(content_types, "Default", {
        "Extension": "rels",
        "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(content_types, "Default", {
        "Extension": "model",
        "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"})
    ET.SubElement(content_types, "Default", {
        "Extension": "config",
        "ContentType": "application/xml"})

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
        zf.writestr("3D/3dmodel.model", model_xml)
        if assembly_id is not None:
            zf.writestr("Metadata/model_settings.config",
                        _model_settings_config(assembly_id, title,
                                               part_objects, by_id))
    return buf.getvalue()
