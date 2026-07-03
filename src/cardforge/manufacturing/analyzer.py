"""Manufacturing analyzer — checks a compiled document against a profile.

v2: consumes the kernel's CompileTrace (real post-layout feature facts) and
CompiledScene (real per-material volumes) instead of walking a geometry IR.
The rules themselves (rules.py) are unchanged pure functions.
"""

from __future__ import annotations

from typing import List, Optional

from cardforge.document.schema_v2 import DocumentV2
from cardforge.kernel.types import CompiledScene, CompileTrace, FeatureRecord
from cardforge.manufacturing.issues import ManufacturingIssue
from cardforge.manufacturing.metrics import ManufacturingMetrics
from cardforge.manufacturing.profiles import ManufacturingProfile
from cardforge.manufacturing.report import ManufacturingReport
from cardforge.manufacturing.rules import (
    check_deboss_depth,
    check_emboss_height,
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
            issues.extend(self._check_record(r, metrics))

        metrics.feature_count = len(trace.records)
        metrics.estimated_materials = sorted(scene.non_empty().keys())
        metrics.estimated_colors = len(metrics.estimated_materials)

        return ManufacturingReport(
            profile=self.profile, issues=issues, metrics=metrics)

    def _check_record(self, r: FeatureRecord,
                      metrics: ManufacturingMetrics) -> List[ManufacturingIssue]:
        issues: List[ManufacturingIssue] = []
        p = self.profile
        nid = r.feature_id

        issues.extend(check_unsupported_relief(r.relief_mode, nid, p))

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


def profile_by_name(name: str) -> ManufacturingProfile:
    profiles = {
        "fdm-standard": ManufacturingProfile.fdm_standard,
        "fdm-fine": ManufacturingProfile.fdm_fine,
        "sla": ManufacturingProfile.sla_standard,
        "sla-standard": ManufacturingProfile.sla_standard,
    }
    return profiles.get(name, ManufacturingProfile.fdm_standard)()
