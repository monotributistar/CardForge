"""Constraint checks over a compiled document.

Relocated from domain/constraints.py, now driven by the CompileTrace (real
post-layout bounds) instead of raw feature declarations — the checks see the
same geometry the export uses.
"""

from __future__ import annotations

from typing import List

from cardforge.document.schema_v2 import DocumentV2
from cardforge.kernel.types import (
    Bounds, CompileTrace, ConstraintIssue, Severity,
)

MIN_FEATURE_MM = 0.6
MIN_QR_MM = 22.0
QR_QUIET_MM = 2.0
SAFE_MARGIN_MM = 1.0

# Thinnest floor (or printed lid) left around a pocket. Under this the wall
# over an insert flexes, cracks, or shows the magnet through.
MIN_POCKET_WALL_MM = 0.8
# The floor is a difference of authored millimetres (thickness − ceiling −
# depth), so a design that hits the minimum exactly lands a few ulps under it.
# Without this slack the wizard's own "thick enough" cards warn about
# themselves.
_WALL_EPS = 1e-6


def _colored_faces(doc: DocumentV2) -> set:
    """Faces an outline colour LAYER is visible on (empty unless the outline
    is a multicolor SVG with colorDepth — through-columns colour both faces
    and constrain nothing)."""
    o = doc.object.outline
    if o.type != "path" or not o.svg_inline or not o.color_map or not o.color_depth:
        return set()
    base_id = doc.base_material.id
    if not any(m != base_id for m in o.color_map.values()):
        return set()
    return {"front", "back"} if o.color_face == "both" else {o.color_face or "front"}


def check_constraints(doc: DocumentV2, trace: CompileTrace) -> List[ConstraintIssue]:
    issues: List[ConstraintIssue] = []
    outline = Bounds(0, 0, doc.object.outline.width, doc.object.outline.height)
    thickness = doc.object.thickness
    colored = _colored_faces(doc)
    color_depth = doc.object.outline.color_depth if colored else 0.0

    # 0. The colour layer must be thick enough to actually print in colour:
    #    under two layers the base below bleeds through.
    layer_h = doc.manufacturing.layer_height
    if color_depth and layer_h > 0 and color_depth < 2 * layer_h:
        issues.append(ConstraintIssue(
            Severity.WARNING, "color-layer-too-thin",
            f"The outline colour layer is {color_depth}mm — under two "
            f"{layer_h}mm layers, so the base below will show through. "
            f"Use at least {2 * layer_h:g}mm."))

    records = trace.records
    for r in records:
        loc = dict(feature_id=r.feature_id, face_id=r.face_id)

        # 1. Minimum printable size (full-face patterns exempt: their bounds
        #    are the outline by construction)
        if r.type not in ("pattern", "text-pattern"):
            if r.bounds.width < MIN_FEATURE_MM or r.bounds.height < MIN_FEATURE_MM:
                issues.append(ConstraintIssue(
                    Severity.ERROR, "min-feature-size",
                    f"Feature is {r.bounds.width:.2f}×{r.bounds.height:.2f}mm; "
                    f"minimum printable size is {MIN_FEATURE_MM}mm", **loc))

        # 2. Inside the object outline. Holes are exempt: with a tab they
        #    legitimately live (partly) outside the outline, and without one
        #    the compiler already emits the specific "open notch" warning.
        if not outline.contains(r.bounds) and r.type != "hole":
            issues.append(ConstraintIssue(
                Severity.ERROR, "outside-bounds",
                f"Feature extends outside the object outline "
                f"(bounds {r.bounds.x:.1f},{r.bounds.y:.1f} "
                f"{r.bounds.width:.1f}×{r.bounds.height:.1f}mm)", **loc))
        # 2b. Cut off by the object's shape. Distinct from 2: on an SVG
        #     silhouette the bounds can sit entirely inside the outline's box
        #     while the artwork's contour still slices the feature. A clipped
        #     QR no longer scans, so that one is an error.
        clipped = r.extra.get("clipped_pct", 0.0)
        if clipped >= 1.0 and r.type not in ("hole", "pattern", "text-pattern"):
            issues.append(ConstraintIssue(
                Severity.ERROR if r.type == "qr" else Severity.WARNING,
                "clipped-by-outline",
                f"{clipped:.0f}% of this feature falls outside the object "
                f"shape and was cut off — move it inward or make it smaller",
                **loc))

        # 3. Safe margin (warning). Edge-hugging decorations are exempt:
        #    frames and corner marks legitimately live at the border — and so
        #    do holes (a lanyard slot hugs the edge by design).
        edge_decoration = r.extra.get("shape_type") in ("frame", "corner-marks")
        if outline.contains(r.bounds) \
                and not outline.expand(-SAFE_MARGIN_MM).contains(r.bounds) \
                and r.type not in ("pattern", "text-pattern", "hole") \
                and not edge_decoration:
            issues.append(ConstraintIssue(
                Severity.WARNING, "safe-margin",
                f"Feature is within {SAFE_MARGIN_MM}mm of the object edge", **loc))

        # 4. QR sizing/contrast/quiet-zone live in the manufacturing analyzer
        #    (nozzle-aware), not here — this stays purely geometric.

        # 5. Relief depth vs thickness
        if r.relief_mode in ("deboss", "flush", "deboss-backed"):
            if r.relief_value >= thickness:
                issues.append(ConstraintIssue(
                    Severity.ERROR, "depth-exceeds-thickness",
                    f"{r.relief_mode} depth {r.relief_value}mm ≥ object thickness "
                    f"{thickness}mm — use a cut instead", **loc))

        # 5b. Carving from one face into the OTHER face's colour layer eats
        #     the artwork from behind: what shows there is this feature's
        #     material, not the logo's colour.
        if r.relief_mode in ("deboss", "flush", "deboss-backed"):
            far = "back" if r.face_id == "front" else "front"
            if far in colored and r.relief_value > thickness - color_depth:
                issues.append(ConstraintIssue(
                    Severity.WARNING, "carve-reaches-color-layer",
                    f"{r.relief_mode} {r.relief_value}mm cuts into the {far} "
                    f"colour layer — only {thickness - color_depth:g}mm of base "
                    f"separates the faces. Keep it under that.", **loc))

        # 5c. Pocket: the cavity is sized for a real object, so what matters
        #     is the material LEFT around it — the floor under the insert,
        #     the lid over it — and whether the bore was opened up enough for
        #     the insert to go in at all.
        if r.type == "pocket":
            d = float(r.extra.get("pocket_depth_mm", 0.0))
            ceiling = float(r.extra.get("pocket_ceiling_mm", 0.0))
            clearance = float(r.extra.get("pocket_clearance_mm", 0.0))
            insert = str(r.extra.get("pocket_insert", "insert"))
            floor = thickness - ceiling - d
            min_wall = max(MIN_POCKET_WALL_MM, 2 * layer_h)

            if floor <= 0:
                issues.append(ConstraintIssue(
                    Severity.ERROR, "pocket-breaks-through",
                    f"The pocket is {d:.2f}mm deep under a {ceiling:.2f}mm lid — "
                    f"that needs more than the {thickness:g}mm thickness, so it "
                    f"opens through the other face. Reduce the depth or the "
                    f"ceiling, or make the object thicker.", **loc))
            elif floor < min_wall - _WALL_EPS:
                issues.append(ConstraintIssue(
                    Severity.WARNING, "pocket-floor-too-thin",
                    f"Only {floor:.2f}mm of material is left under the pocket; "
                    f"use at least {min_wall:g}mm or the floor will crack and "
                    f"the {insert} will push through.", **loc))

            if ceiling > 0:
                if ceiling < min_wall - _WALL_EPS:
                    issues.append(ConstraintIssue(
                        Severity.WARNING, "pocket-ceiling-too-thin",
                        f"The lid over the pocket is {ceiling:.2f}mm and has to "
                        f"bridge the whole bore; use at least {min_wall:g}mm.",
                        **loc))
                # The insert goes in mid-print — say exactly when.
                pause_z = ceiling + d if r.face_id == "back" else thickness - ceiling
                issues.append(ConstraintIssue(
                    Severity.WARNING, "pocket-needs-print-pause",
                    f"The pocket is sealed by a {ceiling:.2f}mm lid, so the "
                    f"{insert} cannot be dropped in afterwards: pause the print "
                    f"at z = {pause_z:.2f}mm, place it, and resume.", **loc))

            if clearance <= 0:
                issues.append(ConstraintIssue(
                    Severity.WARNING, "pocket-no-clearance",
                    f"The bore is cut at the {insert}'s exact nominal diameter. "
                    f"Printed holes come out undersized — add some clearance "
                    f"(0.2mm is a good starting point) or it will not fit.",
                    **loc))

            # A pocket carved from one face reaches into the other face's
            # colour layer just like any other cavity.
            far = "back" if r.face_id == "front" else "front"
            if far in colored and ceiling + d > thickness - color_depth:
                issues.append(ConstraintIssue(
                    Severity.WARNING, "carve-reaches-color-layer",
                    f"The pocket reaches {ceiling + d:.2f}mm into the body and "
                    f"eats the {far} colour layer from behind — only "
                    f"{thickness - color_depth:g}mm of base separates the faces.",
                    **loc))

        # 6. Emboss on the bed-facing (back) face is not printable. That face
        #    rests on the print bed and must stay flat — only carving (deboss/
        #    cut) or flush inlays are allowed there.
        if r.face_id == "back" and r.relief_mode == "emboss":
            issues.append(ConstraintIssue(
                Severity.ERROR, "back-emboss-not-flat",
                "The bed-facing (back) face must stay flat — it prints against "
                "the bed. Use deboss/cut to carve, or flush to inlay, instead "
                "of emboss.", **loc))

    # 7. Overlap between features on the same face (warning; the kernel
    #    resolves overlaps deterministically, but they are usually authoring
    #    mistakes). Full-face patterns are exempt.
    solid = [r for r in records if r.type not in ("pattern", "text-pattern")]
    for i, a in enumerate(solid):
        for b in solid[i + 1:]:
            if a.face_id == b.face_id and a.bounds.intersects(b.bounds):
                issues.append(ConstraintIssue(
                    Severity.WARNING, "overlap",
                    f"Features '{a.feature_id}' and '{b.feature_id}' overlap "
                    f"on face {a.face_id}",
                    feature_id=b.feature_id, face_id=b.face_id))

    return issues
