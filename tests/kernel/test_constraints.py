"""Tests for kernel constraint checks (relocated from domain/constraints.py)."""

import pytest

from cardforge.kernel.compile import compile_document
from cardforge.kernel.constraints import check_constraints
from cardforge.kernel.types import Severity

from tests.kernel.test_compile import make_doc, square


def issues_for(doc):
    scene, trace = compile_document(doc)
    return check_constraints(doc, trace)


def codes(issues):
    return [i.code for i in issues]


class TestConstraints:
    def test_clean_document_no_issues(self):
        doc = make_doc(front=[square("ok", 10, 10, 10, "text",
                                     {"mode": "emboss", "height": 0.4})])
        assert issues_for(doc) == []

    def test_outside_bounds_error(self):
        doc = make_doc(front=[square("out", 55, 10, 10, "text",
                                     {"mode": "emboss", "height": 0.4})])
        issues = issues_for(doc)
        assert "outside-bounds" in codes(issues)
        assert issues[codes(issues).index("outside-bounds")].severity == Severity.ERROR

    def test_safe_margin_warning(self):
        doc = make_doc(front=[square("edge", 0.5, 10, 10, "text",
                                     {"mode": "emboss", "height": 0.4})])
        issues = issues_for(doc)
        assert "safe-margin" in codes(issues)

    def test_min_feature_size_error(self):
        doc = make_doc(front=[square("tiny", 10, 10, 0.4, "text",
                                     {"mode": "emboss", "height": 0.4})])
        assert "min-feature-size" in codes(issues_for(doc))

    def test_qr_too_small_warning(self):
        doc = make_doc(front=[{
            "id": "q", "type": "qr", "transform": {"x": 10, "y": 10},
            "material": "text", "relief": {"mode": "emboss", "height": 0.4},
            "qrType": "url", "fields": {"url": "https://x.dev"}, "size": 15,
        }])
        assert "qr-too-small" in codes(issues_for(doc))

    def test_depth_exceeds_thickness_error(self):
        doc = make_doc(front=[square("deep", 10, 10, 10, "base",
                                     {"mode": "deboss", "depth": 2.5})])
        issues = issues_for(doc)
        assert "depth-exceeds-thickness" in codes(issues)

    def test_back_emboss_warning(self):
        doc = make_doc(back=[square("b", 10, 10, 10, "text",
                                    {"mode": "emboss", "height": 0.4})])
        assert "back-emboss-on-bed" in codes(issues_for(doc))

    def test_overlap_warning(self):
        doc = make_doc(front=[
            square("a", 10, 10, 10, "text", {"mode": "emboss", "height": 0.4}),
            square("b", 15, 12, 10, "accent", {"mode": "emboss", "height": 0.4}),
        ])
        issues = issues_for(doc)
        assert "overlap" in codes(issues)

    def test_full_face_pattern_exempt_from_size_checks(self):
        doc = make_doc(front=[{
            "id": "p", "type": "pattern", "patternType": "dots", "spacing": 4,
            "region": "face", "transform": {"x": 0, "y": 0},
            "material": "base", "relief": {"mode": "deboss", "depth": 0.2},
        }])
        assert "safe-margin" not in codes(issues_for(doc))
