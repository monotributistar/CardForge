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
from cardforge.kernel.features import (build_feature_shapes,
                                       outline_color_regions,
                                       outline_cross_section)
from cardforge.kernel.patterns import PatternDensityError
from cardforge.kernel import shapes2d as s2
from cardforge.kernel.types import Bounds, CompiledScene, CompileTrace, ScenePart

_EPS = 1e-9

# Default backing-pad height over a SOLID base (mm). Over a lattice the pad
# stays full-thickness — it must reach the bed to support the feature.
_DEFAULT_PAD_MM = 0.6


@dataclass
class _SolidOp:
    priority: Tuple[int, int]      # (z_order, sequence)
    material: str
    solid: Manifold
    part_id: str = ""              # part id (feature id + suffixes)
    feature_id: str = ""           # owning feature (keep-out exemption)
    face: str = ""                 # face that owns this op


@dataclass
class _Claim:
    """Exclusion zone. `priority` gates only SAME-face features — zOrder is
    a per-face layer order, comparing it across faces is meaningless.
    Across faces: a claim always applies (each face owns its z-band), except
    `background` claims (backing plates), which never reach the other face."""
    priority: Tuple[int, int]
    feature_id: str
    prism: Manifold
    face: str
    background: bool = False

    def applies_to(self, other_face: str, other_priority: Tuple[int, int]) -> bool:
        if self.face == other_face:
            return self.priority > other_priority
        return not self.background


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
    part_names: Dict[str, str] = {}    # part id → display name
    # (priority, feature_id, solid, face): cavities + inlay pockets
    base_subtracts: List[Tuple[Tuple[int, int], str, Manifold, str]] = []
    # Exclusion zones (e.g. QR quiet zone) — lower-priority same-face
    # features (and the other face's backing pads) lose geometry AND carves
    # inside these.
    claims: List[_Claim] = []
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
            try:
                fs = build_feature_shapes(doc, face_id, feature, outline_phys, asset_root)
            except PatternDensityError as e:
                # Degenerate spacing (zero/negative or absurd tile count):
                # skip the feature instead of stalling or crashing the compile.
                trace.skipped.append(feature.id)
                trace.warnings.append(f"{face_id}/{feature.id}: {e}")
                continue
            if fs.skip_reason:
                trace.skipped.append(feature.id)
                trace.warnings.append(f"{face_id}/{feature.id}: {fs.skip_reason}")
                continue
            trace.records.append(fs.record)

            # ── Hole: always a through-cut; optional material tab ─────────
            # The cutter is NOT clipped to the outline — with a tab the hole
            # lives (partly) outside it (keyring ear, lanyard lug). The tab
            # footprint is fused into the base region: solid, full thickness,
            # base material, and later pierced by the cut like everything else.
            if feature.type == "hole":
                hole_region = outline_phys
                if fs.tab is not None and not fs.tab.is_empty():
                    tab_cs = fs.tab
                    if is_back:
                        tab_cs = tab_cs.mirror((1, 0)).translate((W, 0))
                    base_backing_2d.append(tab_cs)
                    hole_region = hole_region + tab_cs
                for _mat, cs in fs.shapes:
                    if cs.is_empty():
                        continue
                    if is_back:
                        cs = cs.mirror((1, 0)).translate((W, 0))
                    cut_shapes.append(cs)
                    if not (cs - hole_region).is_empty():
                        trace.warnings.append(
                            f"{face_id}/{feature.id}: hole extends beyond the "
                            "object edge (open notch) — enable its tab or move "
                            "it inward")
                continue

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

                display = feature.name or feature.id
                part_id = (feature.id if mat == feature.material
                           else f"{feature.id}:{mat}")
                part_names[part_id] = (display if mat == feature.material
                                       else f"{display} ({mat})")
                part_names[f"{feature.id}-floor"] = f"{display} floor"
                part_names[f"{feature.id}-pad"] = f"{display} pad"

                if relief.mode == "emboss":
                    # Front (presentation) face only — back emboss was rejected
                    # above. Emboss sits on the top surface, growing upward.
                    adds.append(_SolidOp((feature.z_order, seq), mat,
                                         _extrude_at(cs, relief.height, T),
                                         part_id, feature.id, face_id))

                elif relief.mode == "deboss":
                    d = min(relief.depth, T - _EPS)
                    z0 = T - d if not is_back else 0.0
                    base_subtracts.append(((feature.z_order, seq), feature.id,
                                           _extrude_at(cs, d, z0), face_id))
                    if mat != base_mat:
                        trace.warnings.append(
                            f"{face_id}/{feature.id}: deboss is an empty cavity; "
                            f"material '{mat}' ignored (use flush or deboss-backed)")

                elif relief.mode == "flush":
                    d = min(relief.depth, T - _EPS)
                    z0 = T - d if not is_back else 0.0
                    pocket = _extrude_at(cs, d, z0)
                    base_subtracts.append(((feature.z_order, seq), feature.id,
                                           pocket, face_id))
                    if mat == base_mat:
                        trace.warnings.append(
                            f"{face_id}/{feature.id}: flush inlay in base material "
                            "has no visible effect")
                    adds.append(_SolidOp((feature.z_order, seq), mat, pocket,
                                         part_id, feature.id, face_id))

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
                    base_subtracts.append(((feature.z_order, seq), feature.id,
                                           _extrude_at(cs, d, z_cav), face_id))
                    # floor plug sits at the cavity floor
                    z_floor = z_cav if not is_back else d - ft
                    adds.append(_SolidOp((feature.z_order, seq),
                                         relief.floor_material,
                                         _extrude_at(cs, ft, z_floor),
                                         f"{feature.id}-floor", feature.id, face_id))
                else:
                    trace.warnings.append(
                        f"{face_id}/{feature.id}: unknown relief mode '{relief.mode}'")

            # ── Keep-out (e.g. QR quiet zone) ──────────────────────────────
            # The feature reserves a region beyond its own geometry: any
            # LOWER-priority feature loses adds and carves inside it, so a
            # background pattern can't invade a QR's quiet zone. Same-feature
            # geometry (modules, pad, floor) is exempt.
            if fs.keepout is not None and not fs.keepout.is_empty():
                ko = fs.keepout
                if is_back:
                    ko = ko.mirror((1, 0)).translate((W, 0))
                ko = ko ^ outline_phys
                if not ko.is_empty():
                    if relief.mode == "emboss":
                        prism = _extrude_at(ko, relief.height, T)
                    elif relief.mode == "cut":
                        prism = _extrude_at(ko, 4 * T + 2.0, -(2 * T + 1.0))
                    else:  # deboss / flush / deboss-backed
                        d = min(relief.depth, T - _EPS)
                        z0 = T - d if not is_back else 0.0
                        prism = _extrude_at(ko, d, z0)
                    claims.append(_Claim((feature.z_order, seq), feature.id,
                                         prism, face_id))

            # ── Backing pad: support + visible background plate ───────────
            # A PLATE covering the feature's bounds (expanded by padding; QR
            # defaults to its quiet zone) — not the raw glyph/module shapes,
            # which would vanish behind the feature itself. Serves two roles:
            # keeping features from floating over a lattice, and giving a
            # feature a contrasting background (e.g. QR on the bed face).
            # 'auto' pads only over a lattice; 'on' always; 'off' never.
            b = feature.backing
            mode = b.mode if b else "auto"
            need_pad = (mode == "on" or (mode == "auto" and lattice)) \
                and relief.mode != "cut" and not footprint.is_empty()
            if need_pad:
                pad_mat = (b.material if (b and b.material) else base_mat)
                thk = (b.thickness if (b and b.thickness) else 0.0)
                # Default margin: QR uses its quiet zone; anything else gets
                # 1.5mm of breathing room so the plate reads as a plaque
                # instead of hugging the glyphs.
                margin = (b.padding if (b and b.padding) else
                          (feature.quiet_zone if feature.type == "qr" else 1.5))
                x0, y0, x1, y1 = footprint.bounds()
                if b and b.shape == "circle":
                    # Centered disc: diameter = larger bounds side + padding.
                    dia = max(x1 - x0, y1 - y0) + 2 * margin
                    plate = s2.circle(dia).translate(
                        ((x0 + x1) / 2 - dia / 2, (y0 + y1) / 2 + dia / 2))
                else:
                    plate = CrossSection([[
                        (x0 - margin, y0 - margin), (x1 + margin, y0 - margin),
                        (x1 + margin, y1 + margin), (x0 - margin, y1 + margin),
                    ]])
                plate = plate ^ outline_phys
                if pad_mat == base_mat and thk <= 0:
                    # Full-thickness solid plate, folded into the base region
                    # so subtracts/emboss then apply over solid.
                    base_backing_2d.append(plate)
                    h, z0 = T, 0.0
                else:
                    # Default height: full thickness over a lattice (the pad
                    # must reach the bed to support the feature); a thin
                    # plate over a solid base — a through-column would show
                    # on the opposite face.
                    if thk <= 0:
                        h = T if lattice else min(_DEFAULT_PAD_MM, T)
                    else:
                        h = min(thk, T)
                    z0 = 0.0 if (h >= T - _EPS or is_back) else T - h
                    pad = _extrude_at(plate, h, z0)
                    # carve base so pad is disjoint
                    base_subtracts.append(((feature.z_order - 1000, seq),
                                           feature.id, pad, face_id))
                    adds.append(_SolidOp((feature.z_order - 1000, seq), pad_mat, pad,
                                         f"{feature.id}-pad", feature.id, face_id))
                # The plate is also a keep-out AT THE FEATURE'S priority:
                # lower-layer features must not spill onto the plaque, carve
                # under it, or emboss on top of it (its whole point is a
                # clean contrasting zone — the icon/QR "quiet zone"). The
                # claim is the full column incl. emboss headroom; embossing
                # ON a plaque stays possible by layering the other feature
                # ABOVE the plaque's owner (higher zOrder).
                # `background`: the plaque never claims against the OTHER
                # face — zOrder is per-face, and a full-thickness pad must
                # not swallow e.g. a QR inlaid on the opposite side.
                claims.append(_Claim((feature.z_order, seq), feature.id,
                                     _extrude_at(plate, 2 * T + 1.0, 0.0),
                                     face_id, background=True))

    # ── Assembly ───────────────────────────────────────────────────────────
    if base_backing_2d:
        region = base_region_2d
        for fp in base_backing_2d:
            region = region + fp
        base_region_2d = region
    base = _extrude_at(base_region_2d, T, 0.0)

    # Carve cavities/pockets — but a carve loses any region inside a
    # higher-priority OTHER feature's keep-out (a pattern's deboss must not
    # pit a QR's quiet zone).
    for prio, fid, sub, face in base_subtracts:
        for c in claims:
            if c.feature_id != fid and c.applies_to(face, prio):
                sub = sub - c.prism
        base = base - sub

    # Disjointness: a solid loses any region claimed by a higher-priority add.
    # Applied across ALL parts (not just other materials) so every part is
    # pairwise disjoint and the 3MF can expose one part per feature.
    ordered = sorted(adds, key=lambda op: op.priority)
    part_solids: Dict[str, Tuple[str, Manifold]] = {}  # part id → (material, solid)
    part_order: List[str] = []
    for i, op in enumerate(ordered):
        solid = op.solid
        for later in ordered[i + 1:]:
            if later.part_id != op.part_id:
                solid = solid - later.solid
        # keep-outs of higher-priority OTHER features also claim the space
        for c in claims:
            if c.feature_id != op.feature_id and c.applies_to(op.face, op.priority):
                solid = solid - c.prism
        if op.part_id in part_solids:
            part_solids[op.part_id] = (op.material,
                                       part_solids[op.part_id][1] + solid)
        else:
            part_solids[op.part_id] = (op.material, solid)
            part_order.append(op.part_id)

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
        base = base - cutter
        part_solids = {pid: (mat, solid - cutter)
                       for pid, (mat, solid) in part_solids.items()}

    # ── Multicolor SVG outline: split the (already carved and cut) base
    # into full-thickness per-material columns. Splitting LAST means every
    # cavity, cut, and lattice op above applied once to the whole body —
    # the color regions only partition what is left.
    parts: List[ScenePart] = []
    for mat, region in outline_color_regions(doc):
        prism = _extrude_at(region, 4 * T + 2.0, -(2 * T + 1.0))
        piece = base ^ prism
        if piece.is_empty():
            continue
        base = base - prism
        parts.append(ScenePart(f"base:{mat}", mat, piece, f"base ({mat})"))
    parts.insert(0, ScenePart("base", base_mat, base, "base"))
    parts += [ScenePart(pid, *part_solids[pid], name=part_names.get(pid, pid))
              for pid in part_order]

    # Per-material volumes are the union of that material's parts
    volumes: Dict[str, Manifold] = {m.id: Manifold() for m in doc.materials}
    for p in parts:
        volumes[p.material] = volumes[p.material] + p.solid

    trace.elapsed_ms = (time.perf_counter() - t0) * 1000
    scene = CompiledScene(
        volumes=volumes,
        thickness=T,
        outline_bounds=Bounds(0, 0, W, H),
        material_order=[m.id for m in doc.materials],
        parts=parts,
    )
    return scene, trace
