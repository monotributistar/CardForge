#!/usr/bin/env python3
"""3MF package generator — creates .3mf file from STL parts with material colors."""

import zipfile
import io
from pathlib import Path
from typing import Dict, List
from xml.etree import ElementTree as ET
from datetime import datetime


def _create_3mf_xml(parts: List[Dict], output_dir: Path) -> Path:
    """Create a 3MF file from STL parts with assigned materials.

    Args:
        parts: List of {name, stl_path, color_hex, material_name} dicts
        output_dir: Directory to write the .3mf file

    Returns:
        Path to the generated .3mf file
    """
    output_path = output_dir / "card.3mf"

    NS_3MF = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
    NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
    NS_MB = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    NS_DC = "http://purl.org/dc/elements/1.1/"

    # Register namespaces
    ET.register_namespace("", NS_3MF)
    ET.register_namespace("ct", NS_CT)
    ET.register_namespace("rel", NS_REL)

    # Build the 3D model
    model = ET.Element(f"{{{NS_3MF}}}model", {
        "unit": "millimeter",
        f"{{{NS_CT}}}lang": "en",
    })

    resources = ET.SubElement(model, "resources")
    build = ET.SubElement(model, "build")

    for idx, part in enumerate(parts):
        obj_id = str(idx + 1)

        # Resource: mesh object
        obj = ET.SubElement(resources, "object", {
            "id": obj_id,
            "type": "model",
            "name": part.get("name", f"part-{idx}"),
        })
        mesh = ET.SubElement(obj, "mesh")

        # Vertices and triangles from STL
        stl_path = part.get("stl_path")
        if stl_path and Path(stl_path).exists():
            verts, tris = _read_stl(Path(stl_path))
            vertices_el = ET.SubElement(mesh, "vertices")
            for v in verts:
                ET.SubElement(vertices_el, "vertex", {"x": f"{v[0]:.4f}", "y": f"{v[1]:.4f}", "z": f"{v[2]:.4f}"})
            triangles_el = ET.SubElement(mesh, "triangles")
            for t in tris:
                ET.SubElement(triangles_el, "triangle", {
                    "v1": str(t[0]), "v2": str(t[1]), "v3": str(t[2]),
                })

        # Color (if available)
        color = part.get("color_hex", "#808080").lstrip("#")
        if len(color) == 6:
            r = int(color[0:2], 16) / 255
            g = int(color[2:4], 16) / 255
            b = int(color[4:6], 16) / 255
            a = 1.0
        else:
            r, g, b, a = 0.5, 0.5, 0.5, 1.0

        # Base materials resource (one per color)
        basematerials = ET.SubElement(resources, "basematerials", {
            "id": f"bm{obj_id}",
        })
        ET.SubElement(basematerials, "base", {
            "name": part.get("material_name", "PLA"),
            "displaycolor": f"#{color}",
        })

        # Build item
        ET.SubElement(build, "item", {
            "objectid": obj_id,
        })

    # Metadata
    metadata = ET.Element(f"{{{NS_MB}}}coreProperties")
    ET.SubElement(metadata, f"{{{NS_DC}}}creator").text = "CardForge"
    ET.SubElement(metadata, f"{{{NS_DC}}}created").text = datetime.now().isoformat()

    # Content types
    content_types = ET.Element("Types", {f"xmlns": NS_CT})
    ET.SubElement(content_types, "Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(content_types, "Default", {"Extension": "model", "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"})
    ET.SubElement(content_types, "Default", {"Extension": "xml", "ContentType": "application/xml"})

    # Relationships
    rels = ET.Element("Relationships", {f"xmlns": NS_REL})
    ET.SubElement(rels, "Relationship", {
        "Id": "rel0",
        "Type": "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel",
        "Target": "/3D/3dmodel.model",
    })

    # Write ZIP
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _xml_str(content_types))
        zf.writestr("_rels/.rels", _xml_str(rels))
        zf.writestr("3D/3dmodel.model", _xml_str(model))
        zf.writestr("Metadata/core-properties.xml", _xml_str(metadata))

    return output_path


def _read_stl(path: Path):
    """Read a binary STL file and return (vertices, triangles)."""
    import struct

    with open(path, "rb") as f:
        f.read(80)  # header
        count = struct.unpack("<I", f.read(4))[0]

        verts_list = []
        verts_set = {}
        tris = []

        for _ in range(count):
            f.read(12)  # normal
            v1 = struct.unpack("<fff", f.read(12))
            v2 = struct.unpack("<fff", f.read(12))
            v3 = struct.unpack("<fff", f.read(12))
            f.read(2)  # attr

            idxs = []
            for v in (v1, v2, v3):
                key = (round(v[0], 4), round(v[1], 4), round(v[2], 4))
                if key not in verts_set:
                    verts_set[key] = len(verts_list)
                    verts_list.append(key)
                idxs.append(verts_set[key])
            tris.append(tuple(idxs))

        return verts_list, tris


def _xml_str(el):
    return ET.tostring(el, encoding="unicode", xml_declaration=True)


def generate_3mf(
    parts: List[Dict],
    output_dir: Path,
) -> Path:
    """Generate a 3MF file from STL parts.

    Args:
        parts: [{name: "base", stl_path: Path(...), color_hex: "#333", material_name: "PLA"}]
        output_dir: Where to write card.3mf

    Returns:
        Path to generated .3mf
    """
    return _create_3mf_xml(parts, output_dir)
