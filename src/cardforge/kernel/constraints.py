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


def check_constraints(doc: DocumentV2, trace: CompileTrace) -> List[ConstraintIssue]:
    issues: List[ConstraintIssue] = []
    outline = Bounds(0, 0, doc.object.outline.width, doc.object.outline.height)
    thickness = doc.object.thickness

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
