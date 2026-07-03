#!/usr/bin/env python3
"""Phase 0 spike item 6 — write a 2-material 3MF from Manifold meshes.

Prototype for export/threemf.py. Writes apps/studio/public/spike.3mf so the
Vite dev server serves it at /spike.3mf for the 3MFLoader browser check.
"""

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from manifold3d import Manifold, CrossSection, FillRule

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

NS_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def rounded_rect_cs(w: float, h: float, r: float, segments: int = 8) -> CrossSection:
    """Rounded rectangle centered at origin (prototype for kernel/shapes2d.py)."""
    import math
    pts = []
    corners = [  # (center, start_angle)
        ((w / 2 - r, h / 2 - r), 0.0),
        ((-w / 2 + r, h / 2 - r), math.pi / 2),
        ((-w / 2 + r, -h / 2 + r), math.pi),
        ((w / 2 - r, -h / 2 + r), 3 * math.pi / 2),
    ]
    for (cx, cy), a0 in corners:
        for i in range(segments + 1):
            a = a0 + (math.pi / 2) * i / segments
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return CrossSection([pts], fillrule=FillRule.EvenOdd)


def manifold_to_3mf_mesh(m: Manifold) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    mesh = m.to_mesh()
    verts = [(float(v[0]), float(v[1]), float(v[2])) for v in mesh.vert_properties]
    tris = [(int(t[0]), int(t[1]), int(t[2])) for t in mesh.tri_verts]
    return verts, tris


def write_3mf(parts: list[dict], out_path: Path) -> None:
    """parts: [{name, color (#rrggbb), manifold}] → 3MF with one object per part."""
    model = ET.Element("model", {"unit": "millimeter", "xmlns": NS_CORE})
    resources = ET.SubElement(model, "resources")
    build = ET.SubElement(model, "build")

    # One basematerials group holding all materials (index = part order)
    bm = ET.SubElement(resources, "basematerials", {"id": "1"})
    for part in parts:
        ET.SubElement(bm, "base", {
            "name": part["name"],
            "displaycolor": part["color"].upper(),
        })

    for idx, part in enumerate(parts):
        obj = ET.SubElement(resources, "object", {
            "id": str(idx + 2),
            "type": "model",
            "name": part["name"],
            "pid": "1",
            "pindex": str(idx),
        })
        mesh_el = ET.SubElement(obj, "mesh")
        verts_el = ET.SubElement(mesh_el, "vertices")
        tris_el = ET.SubElement(mesh_el, "triangles")
        verts, tris = manifold_to_3mf_mesh(part["manifold"])
        for x, y, z in verts:
            ET.SubElement(verts_el, "vertex", {"x": f"{x:.6f}", "y": f"{y:.6f}", "z": f"{z:.6f}"})
        for a, b, c in tris:
            ET.SubElement(tris_el, "triangle", {"v1": str(a), "v2": str(b), "v3": str(c)})
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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ET.tostring(content_types, xml_declaration=True, encoding="unicode"))
        zf.writestr("_rels/.rels", ET.tostring(rels, xml_declaration=True, encoding="unicode"))
        zf.writestr("3D/3dmodel.model", ET.tostring(model, xml_declaration=True, encoding="unicode"))


def main() -> int:
    # Base: rounded card slab 30x18x2 — Emboss: box 8x8x1 sitting EXACTLY on top
    # (coincident faces, the case slicers/viewers must accept)
    base = rounded_rect_cs(30, 18, 3).extrude(2.0)
    emboss = CrossSection([[(-4, -4), (4, -4), (4, 4), (-4, 4)]],
                          fillrule=FillRule.EvenOdd).extrude(1.0).translate((0, 0, 2.0))

    parts = [
        {"name": "PLA Negro", "color": "#1A1A2E", "manifold": base},
        {"name": "PLA Dorado", "color": "#D4AF37", "manifold": emboss},
    ]
    out = PROJECT_ROOT / "apps" / "studio" / "public" / "spike.3mf"
    write_3mf(parts, out)

    # Self-verify: reopen the zip, parse XML, count objects/materials
    with zipfile.ZipFile(out) as zf:
        root = ET.fromstring(zf.read("3D/3dmodel.model"))
    objects = root.findall(f".//{{{NS_CORE}}}object")
    bases = root.findall(f".//{{{NS_CORE}}}base")
    tri_counts = [len(o.findall(f".//{{{NS_CORE}}}triangle")) for o in objects]
    ok = len(objects) == 2 and len(bases) == 2 and all(t > 0 for t in tri_counts)
    print(f"{'PASS' if ok else 'FAIL'}  6a. 3MF write+reparse  "
          f"objects={len(objects)} materials={len(bases)} tris={tri_counts} "
          f"size={out.stat().st_size}B → {out.relative_to(PROJECT_ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
