"""Tests for nozzle-derived profiles and the min-detail manufacturing check."""

import pytest

from cardforge.document.schema_v2 import DocumentV2
from cardforge.kernel.compile import compile_document
from cardforge.manufacturing.analyzer import ManufacturingAnalyzer, resolve_profile
from cardforge.manufacturing.issues import IssueCode, Severity
from cardforge.manufacturing.profiles import ManufacturingProfile


def doc(features, nozzle=0.4, process="fdm"):
    mf = {"process": process}
    if nozzle > 0:  # SLA has no nozzle (schema forbids 0)
        mf["nozzle"] = nozzle
    return DocumentV2.from_dict({
        "cardforge": "2.0", "meta": {"id": "t", "name": "T"},
        "object": {"outline": {"type": "rect", "width": 60, "height": 40}, "thickness": 2.0},
        "manufacturing": mf,
        "materials": [
            {"id": "base", "name": "B", "color": "#111111", "role": "base"},
            {"id": "text", "name": "T", "color": "#ffffff", "role": "text"}],
        "faces": {"front": {"features": features}},
    })


def frame(sw):
    return [{"id": "fr", "type": "shape", "shapeType": "frame", "strokeWidth": sw,
             "inset": 2, "transform": {"x": 0, "y": 0}, "material": "text",
             "relief": {"mode": "emboss", "height": 0.4}}]


def analyze(d):
    scene, trace = compile_document(d)
    return ManufacturingAnalyzer(resolve_profile(d)).analyze(d, scene, trace)


def detail_issues(report):
    return [i for i in report.issues if i.code == IssueCode.MIN_DETAIL]


class TestNozzleProfile:
    def test_for_nozzle_derives_thresholds(self):
        p = ManufacturingProfile.for_nozzle(0.4)
        assert p.min_line_width == 0.4
        assert p.min_wall == 0.8
        assert p.min_text_stroke == 0.5

    def test_bigger_nozzle_bigger_minimums(self):
        assert ManufacturingProfile.for_nozzle(0.6).min_line_width > \
            ManufacturingProfile.for_nozzle(0.4).min_line_width

    def test_resolve_uses_document_nozzle(self):
        assert resolve_profile(doc(frame(0.5), nozzle=0.6)).min_line_width == 0.6
        assert resolve_profile(doc(frame(0.5), nozzle=0.25)).min_line_width == 0.25

    def test_resolve_sla_has_no_nozzle_threshold(self):
        p = resolve_profile(doc(frame(0.5), nozzle=0.0, process="sla"))
        assert p.process == "sla"


class TestMinDetailCheck:
    def test_subnozzle_frame_is_error(self):
        issues = detail_issues(analyze(doc(frame(0.15))))
        assert issues and issues[0].severity == Severity.ERROR

    def test_thin_but_ok_frame_no_issue(self):
        assert detail_issues(analyze(doc(frame(0.6)))) == []

    def test_between_half_and_full_nozzle_is_warning(self):
        # a 0.3mm stroke on a 0.4 nozzle: under-extruded, not impossible
        issues = detail_issues(analyze(doc(frame(0.3))))
        assert issues and issues[0].severity == Severity.WARNING

    def test_finer_nozzle_clears_the_same_detail(self):
        # 0.3mm frame errors/warns at 0.4 but is fine at 0.25
        assert detail_issues(analyze(doc(frame(0.3), nozzle=0.25))) == []

    def test_coarser_nozzle_flags_more(self):
        # a 0.5mm stroke is fine at 0.4 but sub-nozzle at 0.6
        assert detail_issues(analyze(doc(frame(0.5), nozzle=0.4))) == []
        assert detail_issues(analyze(doc(frame(0.5), nozzle=0.6))) != []

    def test_cut_feature_not_flagged(self):
        # a thin cut is a hole, not a printable wall
        cut = [{"id": "c", "type": "shape", "shapeType": "frame", "strokeWidth": 0.15,
                "inset": 2, "transform": {"x": 0, "y": 0}, "material": "text",
                "relief": {"mode": "cut"}}]
        assert detail_issues(analyze(doc(cut))) == []
