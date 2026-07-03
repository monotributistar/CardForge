"""Binary STL writer — one file per material, from the same CompiledScene
the 3MF uses (secondary export for single-material workflows)."""

from __future__ import annotations

import struct
from typing import Dict, List

from manifold3d import Manifold

from cardforge.document.schema_v2 import Material
from cardforge.export.threemf import mesh_arrays, normalized_volumes
from cardforge.kernel.types import CompiledScene


def manifold_to_stl(m: Manifold, name: str = "cardforge") -> bytes:
    """Binary STL bytes for one solid."""
    verts, tris = mesh_arrays(m)
    header = name.encode()[:80].ljust(80, b"\0")
    out = bytearray(header)
    out += struct.pack("<I", len(tris))
    for a, b, c in tris:
        va, vb, vc = verts[a], verts[b], verts[c]
        ux = (vb[0] - va[0], vb[1] - va[1], vb[2] - va[2])
        vx = (vc[0] - va[0], vc[1] - va[1], vc[2] - va[2])
        n = (ux[1] * vx[2] - ux[2] * vx[1],
             ux[2] * vx[0] - ux[0] * vx[2],
             ux[0] * vx[1] - ux[1] * vx[0])
        length = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1.0
        out += struct.pack("<fff", n[0] / length, n[1] / length, n[2] / length)
        for v in (va, vb, vc):
            out += struct.pack("<fff", *v)
        out += b"\0\0"  # attribute byte count
    return bytes(out)


def scene_to_stls(scene: CompiledScene, materials: List[Material]) -> Dict[str, bytes]:
    """{material_id → binary STL} for every non-empty material volume.

    Uses the same bed-normalized volumes as the 3MF so both exports match.
    """
    by_id = {m.id: m for m in materials}
    vols = normalized_volumes(scene)
    out: Dict[str, bytes] = {}
    for mid in scene.material_order:
        if mid not in vols:
            continue
        mat = by_id.get(mid)
        out[mid] = manifold_to_stl(vols[mid], name=f"cardforge_{mid}"
                                   + (f"_slot{mat.slot}" if mat and mat.slot else ""))
    return out
