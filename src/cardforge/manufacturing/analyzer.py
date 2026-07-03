"""Manufacturing analyzer — checks a compiled document against a profile.

v2: consumes the kernel's CompileTrace (real post-layout feature facts) and
CompiledScene (real per-material volumes) instead of walking a geometry IR.
The rules themselves (rules.py) are unchanged pure functions.
"""

from __future__ import annotations

from typing import List, Optional

from cardforge.document.schema_v2 import DocumentV2
from cardforge.kernel.types import CompiledScene, CompileTrace, FeatureRecord
from cardforge.manufacturing.issues import IssueCode, ManufacturingIssue, Severity
from cardforge.manufacturing.metrics import ManufacturingMetrics
from cardforge.manufacturing.profiles import ManufacturingProfile
from cardforge.manufacturing.report import ManufacturingReport
from cardforge.manufacturing.rules import (
    check_deboss_depth,
    check_emboss_height,
    check_min_detail,
    check_qr_module_size,
    check_qr_size,
    check_text_size,
    check_unsupported_relief,
)


class ManufacturingAnalyzer:
    """Analyzes a compiled document for manufacturability."""

    def __init__(self, profile: Optional[ManufacturingProfile] = None):
        self.profile = profile or ManufacturingProfile.fdm_standard()

    def analyze(self, doc: DocumentV2, scene: CompiledScene,
                trace: CompileTrace) -> ManufacturingReport:
        issues: List[ManufacturingIssue] = []
        metrics = ManufacturingMetrics()

        for r in trace.records:
            issues.extend(self._check_record(r, metrics, doc))

        issues.extend(self._check_qr_clearance(trace, doc))

        metrics.feature_count = len(trace.records)
        metrics.estimated_materials = sorted(scene.non_empty().keys())
        metrics.estimated_colors = len(metrics.estimated_materials)

        return ManufacturingReport(
            profile=self.profile, issues=issues, metrics=metrics)

    def _check_record(self, r: FeatureRecord, metrics: ManufacturingMetrics,
                      doc: DocumentV2) -> List[ManufacturingIssue]:
        issues: List[ManufacturingIssue] = []
        p = self.profile
        nid = r.feature_id

        issues.extend(check_unsupported_relief(r.relief_mode, nid, p))

        # Thinnest measured wall/stroke vs the nozzle (from kernel/measure).
        min_width = float(r.extra.get("min_width_mm", 0.0))
        if min_width > 0:
            metrics.min_wall = min(metrics.min_wall, min_width)
            issues.extend(check_min_detail(min_width, nid, p, feature_type=r.type))

        if r.relief_mode == "emboss":
            metrics.update_emboss(r.relief_value)
            issues.extend(check_emboss_height(r.relief_value, nid, p))
        elif r.relief_mode in ("deboss", "flush", "deboss-backed"):
            metrics.update_deboss(r.relief_value)
            issues.extend(check_deboss_depth(r.relief_value, nid, p))

        if r.type == "qr":
            modules = int(r.extra.get("qr_modules", 33))
            module_mm = float(r.extra.get("qr_module_mm", 0.0))
            qr_size = modules * module_mm
            metrics.smallest_qr = min(metrics.smallest_qr, qr_size)
            issues.extend(check_qr_size(qr_size, nid, p))
            issues.extend(check_qr_module_size(qr_size, nid, p, modules=modules))
            issues.extend(self._check_qr_scannability(r, doc))

        if r.type in ("text-block", "text-pattern"):
            metrics.text_count += 1
            font_size = float(r.extra.get("font_size", 0.0))
            if font_size:
                metrics.smallest_text = min(metrics.smallest_text, font_size)
                issues.extend(check_text_size(font_size, nid, p))

        if r.type == "pattern":
            element = float(r.extra.get("element_mm", 0.0))
            if element:
                metrics.update_line(element)

        return issues

    def _check_qr_scannability(self, r: FeatureRecord,
                               doc: DocumentV2) -> List[ManufacturingIssue]:
        """Contrast, quiet zone and coloured-inlay opacity for one QR.

        A QR reads only if its modules stand out from the surrounding surface —
        by colour (a different filament) or by shadow (relief). A flush QR in
        the base colour is invisible; a coloured flush inlay on the bed face is
        the ideal (smooth + crisp) but its colour layer must be deep enough to
        print opaque.
        """
        from cardforge.manufacturing.color import contrast_ratio

        issues: List[ManufacturingIssue] = []
        p = self.profile
        nid = r.feature_id
        qr_mat = doc.material_by_id(r.material)
        base_mat = doc.base_material
        ratio = contrast_ratio(qr_mat.color, base_mat.color) if qr_mat and base_mat else 21.0
        has_relief = r.relief_mode in ("emboss", "deboss", "deboss-backed")

        if ratio < 2.5:  # QR colour ≈ surrounding surface
            if not has_relief:  # flush/cut: coplanar, same colour → nothing to see
                issues.append(ManufacturingIssue(
                    code=IssueCode.QR_CONTRAST, severity=Severity.ERROR,
                    message=f"QR uses the base colour with no relief "
                            f"(contrast {ratio:.1f}:1) — it will not scan",
                    node_id=nid,
                    suggestion="Give the QR a contrasting material, or use "
                               "deboss/emboss so it reads by shadow"))
            else:
                issues.append(ManufacturingIssue(
                    code=IssueCode.QR_CONTRAST, severity=Severity.WARNING,
                    message=f"QR only contrasts by shadow (same colour as the "
                            f"base, {ratio:.1f}:1) — verify it scans in the print",
                    node_id=nid,
                    suggestion="A contrasting material scans far more reliably"))

        quiet = float(r.extra.get("qr_quiet_mm", 0.0))
        if 0 < quiet < p.min_qr_quiet_zone:
            issues.append(ManufacturingIssue(
                code=IssueCode.QR_QUIET_ZONE, severity=Severity.WARNING,
                message=f"QR quiet zone {quiet:.1f}mm is below {p.min_qr_quiet_zone:.0f}mm",
                node_id=nid, value=quiet, threshold=p.min_qr_quiet_zone,
                suggestion=f"Keep at least {p.min_qr_quiet_zone:.0f}mm clear around the QR"))

        # Coloured flush inlay (esp. the bed-face technique): the colour layer
        # must be a few layers thick to print opaque rather than translucent.
        if r.relief_mode == "flush" and qr_mat and qr_mat.id != base_mat.id:
            min_opaque = round(2 * p.layer_height, 3)  # ~2 layers prints opaque
            if 0 < r.relief_value < min_opaque:
                issues.append(ManufacturingIssue(
                    code=IssueCode.QR_OPACITY, severity=Severity.WARNING,
                    message=f"Coloured QR inlay is only {r.relief_value:.2f}mm deep — "
                            f"the colour may print translucent",
                    node_id=nid, value=r.relief_value, threshold=min_opaque,
                    suggestion=f"Use at least {min_opaque:.2f}mm "
                               f"(~2 layers) so the colour is opaque"))
        return issues

    def _check_qr_clearance(self, trace: CompileTrace,
                            doc: DocumentV2) -> List[ManufacturingIssue]:
        """Warn when another feature intrudes into a QR's quiet-zone band."""
        issues: List[ManufacturingIssue] = []
        qrs = [r for r in trace.records if r.type == "qr"]
        for qr in qrs:
            quiet = float(qr.extra.get("qr_quiet_mm", 0.0))
            if quiet <= 0:
                continue
            band = qr.bounds.expand(quiet)
            for other in trace.records:
                if other.feature_id == qr.feature_id or other.face_id != qr.face_id:
                    continue
                if other.type in ("pattern", "text-pattern"):
                    continue  # full-face patterns are background texture
                if band.intersects(other.bounds) and not qr.bounds.intersects(other.bounds):
                    issues.append(ManufacturingIssue(
                        code=IssueCode.QR_QUIET_ZONE, severity=Severity.WARNING,
                        message=f"'{other.feature_id}' sits inside the QR's "
                                f"{quiet:.0f}mm quiet zone — it may block scanning",
                        node_id=other.feature_id,
                        suggestion="Move it clear of the QR's quiet zone"))
        return issues


def profile_by_name(name: str) -> ManufacturingProfile:
    profiles = {
        "fdm-standard": ManufacturingProfile.fdm_standard,
        "fdm-fine": ManufacturingProfile.fdm_fine,
        "sla": ManufacturingProfile.sla_standard,
        "sla-standard": ManufacturingProfile.sla_standard,
    }
    return profiles.get(name, ManufacturingProfile.fdm_standard)()


def resolve_profile(doc: DocumentV2) -> ManufacturingProfile:
    """Build the manufacturing profile from the document.

    The nozzle drives the thresholds: fdm/laser/cnc derive from the actual
    nozzle diameter (so changing it actually changes the alerts); SLA has no
    nozzle and uses its resin preset. A named profile with no nozzle falls
    back to the preset by name.
    """
    mf = doc.manufacturing
    process = (mf.process or "fdm").lower()
    if process == "sla":
        return ManufacturingProfile.sla_standard()
    if mf.nozzle and mf.nozzle > 0:
        return ManufacturingProfile.for_nozzle(
            mf.nozzle, layer_height=mf.layer_height or 0.2, process=process)
    return profile_by_name(mf.profile or "fdm-standard")
