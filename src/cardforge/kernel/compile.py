"""The compile algorithm — document → disjoint per-material volume partition.

Operation order (see plan):
  1. base = extrude(outline, thickness)                    z ∈ [0, T]
  2. collect per-feature ops from both faces
  3. subtract cavities/inlays from base
  4. add emboss/inlay/floor volumes to their materials
  5. enforce disjointness: higher (z_order, seq) wins on overlap
  6. subtract through-cuts from EVERY volume
  7. mirror semantics: back-face features are authored in back-face document
     space and mirrored around the vertical edge into physical space; their
     relief grows downward from z=0.

The result is a CompiledScene {material → Manifold} whose volumes are
pairwise disjoint — the fidelity contract every export shares.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from manifold3d import CrossSection, Manifold

from cardforge.document.schema_v2 import DocumentV2
from cardforge.kernel.base import base_region, is_lattice
from cardforge.kernel.features import build_feature_shapes, outline_cross_section
from cardforge.kernel.types import Bounds, CompiledScene, CompileTrace

_EPS = 1e-9


@dataclass
class _SolidOp:
    priority: Tuple[int, int]      # (z_order, sequence)
    material: str
    solid: Manifold


def _extrude_at(cs: CrossSection, height: float, z0: float) -> Manifold:
    return cs.extrude(height).translate((0, 0, z0))


def compile_document(doc: DocumentV2, asset_root: Path | str = ".") -> Tuple[CompiledScene, CompileTrace]:
    t0 = time.perf_counter()
    asset_root = Path(asset_root)
    trace = CompileTrace()

    W = doc.object.outline.width
    H = doc.object.outline.height
    T = doc.object.thickness
    base_mat = doc.base_material.id

    outline_phys = outline_cross_section(doc)
    base_region_2d = base_region(doc)   # solid outline, or lattice grid + rim
    lattice = is_lattice(doc)

    adds: List[_SolidOp] = []          # emboss / inlay / floor volumes
    base_subtracts: List[Manifold] = []  # cavities + inlay pockets
    cut_shapes: List[CrossSection] = []  # through-holes (physical 2D)
    base_backing_2d: List[CrossSection] = []  # footprints that solidify the base
    seq = 0

    for face_id in ("front", "back"):
        face = doc.faces.get(face_id)
        if face is None:
            continue
        is_back = face_id == "back"

        for feature in sorted(face.features, key=lambda f: f.z_order):
            if not feature.visible:
                continue
            seq += 1
            fs = build_feature_shapes(doc, face_id, feature, outline_phys, asset_root)
            if fs.skip_reason:
                trace.skipped.append(feature.id)
                trace.warnings.append(f"{face_id}/{feature.id}: {fs.skip_reason}")
                continue
            trace.records.append(fs.record)

            relief = feature.relief

            # Bed-facing (back) face must stay flat: it prints against the bed,
            # so raised geometry there is unprintable (it would lift the body off
            # the bed or collide with it). Only carving (deboss/cut) and flush
            # inlays are allowed. Emboss on the back emits NO geometry; the
            # constraint layer raises this as a blocking error (the record above
            # is kept so the feature still appears and the error fires).
            if is_back and relief.mode == "emboss":
                trace.warnings.append(
                    f"{face_id}/{feature.id}: emboss is not allowed on the "
                    "bed-facing face — it must stay flat (use deboss, cut, or flush)")
                continue

            footprint = CrossSection()  # union of this feature's placed shapes
            for mat, cs in fs.shapes:
                if cs.is_empty():
                    continue
                # Back face: mirror around the vertical edge (flip x), then
                # shift back into [0, W]. Clip to the outline so nothing pokes
                # outside a path-shaped border.
                if is_back:
                    cs = cs.mirror((1, 0)).translate((W, 0))
                cs = cs ^ outline_phys
                if cs.is_empty():
                    continue
                footprint = footprint + cs

                if relief.mode == "emboss":
                    # Front (presentation) face only — back emboss was rejected
                    # above. Emboss sits on the top surface, growing upward.
                    adds.append(_SolidOp((feature.z_order, seq), mat,
                                         _extrude_at(cs, relief.height, T)))

                elif relief.mode == "deboss":
                    d = min(relief.depth, T - _EPS)
                    z0 = T - d if not is_back else 0.0
                    base_subtracts.append(_extrude_at(cs, d, z0))
                    if mat != base_mat:
                        trace.warnings.append(
                            f"{face_id}/{feature.id}: deboss is an empty cavity; "
                            f"material '{mat}' ignored (use flush or deboss-backed)")

                elif relief.mode == "flush":
                    d = min(relief.depth, T - _EPS)
                    z0 = T - d if not is_back else 0.0
                    pocket = _extrude_at(cs, d, z0)
                    base_subtracts.append(pocket)
                    if mat == base_mat:
                        trace.warnings.append(
                            f"{face_id}/{feature.id}: flush inlay in base material "
                            "has no visible effect")
                    adds.append(_SolidOp((feature.z_order, seq), mat, pocket))

                elif relief.mode == "cut":
                    cut_shapes.append(cs)

                elif relief.mode == "deboss-backed":
                    d = min(relief.depth, T - _EPS)
                    ft = relief.floor_thickness
                    if ft >= d:
                        trace.warnings.append(
                            f"{face_id}/{feature.id}: floorThickness {ft} >= depth {d}; "
                            "clamped (becomes a flush inlay)")
                        ft = d
                    z_cav = T - d if not is_back else 0.0
                    base_subtracts.append(_extrude_at(cs, d, z_cav))
                    # floor plug sits at the cavity floor
                    z_floor = z_cav if not is_back else d - ft
                    adds.append(_SolidOp((feature.z_order, seq),
                                         relief.floor_material,
                                         _extrude_at(cs, ft, z_floor)))
                else:
                    trace.warnings.append(
                        f"{face_id}/{feature.id}: unknown relief mode '{relief.mode}'")

            # ── Backing pad: keep the feature from floating ────────────────
            # Needed when the base under it is open (a lattice). 'auto' adds a
            # pad only then; 'on' forces one; 'off' never. Cuts never get a pad.
            b = feature.backing
            mode = b.mode if b else "auto"
            need_pad = (mode == "on" or (mode == "auto" and lattice)) \
                and relief.mode != "cut" and not footprint.is_empty()
            if need_pad:
                pad_mat = (b.material if (b and b.material) else base_mat)
                thk = (b.thickness if (b and b.thickness) else 0.0)
                if pad_mat == base_mat and thk <= 0:
                    # Full-thickness solid of the footprint, folded into the
                    # base region so subtracts/emboss then apply over solid.
                    base_backing_2d.append(footprint)
                else:
                    h = T if thk <= 0 else min(thk, T)
                    z0 = 0.0 if (thk <= 0 or is_back) else T - h
                    pad = _extrude_at(footprint, h, z0)
                    base_subtracts.append(pad)  # carve base so pad is disjoint
                    adds.append(_SolidOp((feature.z_order - 1000, seq), pad_mat, pad))

    # ── Assembly ───────────────────────────────────────────────────────────
    if base_backing_2d:
        region = base_region_2d
        for fp in base_backing_2d:
            region = region + fp
        base_region_2d = region
    base = _extrude_at(base_region_2d, T, 0.0)

    for sub in base_subtracts:
        base = base - sub

    volumes: Dict[str, Manifold] = {m.id: Manifold() for m in doc.materials}
    volumes[base_mat] = base

    # Disjointness: a solid loses any region claimed by a higher-priority add
    ordered = sorted(adds, key=lambda op: op.priority)
    for i, op in enumerate(ordered):
        solid = op.solid
        for later in ordered[i + 1:]:
            if later.material != op.material:
                solid = solid - later.solid
        volumes[op.material] = volumes[op.material] + solid

    # Emboss volumes must not claim space occupied by another material's
    # inlay/floor already carved out of base — base was already carved, and
    # adds vs base overlap is impossible by construction (adds live either
    # above the surface or inside carved pockets).

    if cut_shapes:
        all_cuts = cut_shapes[0]
        for cs in cut_shapes[1:]:
            all_cuts = all_cuts + cs
        # Generous z-range so cuts pierce back-face emboss as well
        cutter = _extrude_at(all_cuts, 4 * T + 2.0, -(2 * T + 1.0))
        volumes = {m: v - cutter for m, v in volumes.items()}

    trace.elapsed_ms = (time.perf_counter() - t0) * 1000
    scene = CompiledScene(
        volumes=volumes,
        thickness=T,
        outline_bounds=Bounds(0, 0, W, H),
        material_order=[m.id for m in doc.materials],
    )
    return scene, trace
