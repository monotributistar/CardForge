"""Tests for manufacturing report, metrics, and score."""

import pytest
from cardforge.manufacturing.report import ManufacturingReport, ManufacturingFix
from cardforge.manufacturing.metrics import ManufacturingMetrics
from cardforge.manufacturing.issues import ManufacturingIssue, IssueCode, Severity
from cardforge.manufacturing.profiles import ManufacturingProfile


class TestManufacturingMetrics:
    def test_default_metrics(self):
        m = ManufacturingMetrics()
        assert m.feature_count == 0
        assert m.smallest_line == 999.0
        assert m.largest_line == 0.0

    def test_update_line(self):
        m = ManufacturingMetrics()
        m.update_line(0.8)
        m.update_line(0.4)
        assert m.smallest_line == 0.4
        assert m.largest_line == 0.8

    def test_update_emboss(self):
        m = ManufacturingMetrics()
        m.update_emboss(0.3)
        m.update_emboss(0.6)
        assert m.smallest_emboss == 0.3
        assert m.largest_emboss == 0.6

    def test_update_deboss(self):
        m = ManufacturingMetrics()
        m.update_deboss(0.2)
        assert m.smallest_deboss == 0.2

    def test_update_text(self):
        m = ManufacturingMetrics()
        m.update_text(3.0)
        assert m.smallest_text == 3.0

    def test_to_dict(self):
        m = ManufacturingMetrics()
        m.feature_count = 3
        m.update_line(0.5)
        d = m.to_dict()
        assert d["feature_count"] == 3
        assert d["smallest_line_mm"] == 0.5


class TestManufacturingReport:
    def test_empty_report(self):
        r = ManufacturingReport()
        assert r.issues == []
        assert r.score == 100
        assert r.is_manufacturable
        assert r.score_label.startswith("Excellent")

    def test_with_warnings(self):
        r = ManufacturingReport()
        r.add_issue(ManufacturingIssue(
            code=IssueCode.MIN_EMBOSS, severity=Severity.WARNING,
            message="low emboss",
        ))
        assert r.score == 95
        assert r.is_manufacturable
        assert "Excellent" in r.score_label

    def test_with_errors(self):
        r = ManufacturingReport()
        r.add_issue(ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL, severity=Severity.ERROR,
            message="QR too small",
        ))
        assert r.score == 85
        assert not r.is_manufacturable

    def test_with_fatal(self):
        r = ManufacturingReport()
        r.add_issue(ManufacturingIssue(
            code=IssueCode.MIN_LINE_WIDTH, severity=Severity.FATAL,
            message="missing base",
        ))
        assert r.score == 60
        assert not r.is_manufacturable

    def test_mixed_issues(self):
        r = ManufacturingReport()
        r.add_issue(ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL, severity=Severity.ERROR, message="a"))
        r.add_issue(ManufacturingIssue(
            code=IssueCode.MIN_EMBOSS, severity=Severity.WARNING, message="b", suggestion="fix it"))
        assert r.score == 80
        assert len(r.errors) == 1
        assert len(r.warnings) == 1
        assert len(r.suggestions) == 1

    def test_multiple_errors_lower_score(self):
        r = ManufacturingReport()
        for _ in range(4):
            r.add_issue(ManufacturingIssue(
                code=IssueCode.QR_TOO_SMALL, severity=Severity.ERROR, message="x"))
        assert r.score == 40

    def test_score_bottom_zero(self):
        r = ManufacturingReport()
        for _ in range(10):
            r.add_issue(ManufacturingIssue(
                code=IssueCode.MIN_LINE_WIDTH, severity=Severity.FATAL, message="x"))
        assert r.score == 0

    def test_score_label_poor(self):
        r = ManufacturingReport()
        for _ in range(3):
            r.add_issue(ManufacturingIssue(
                code=IssueCode.QR_TOO_SMALL, severity=Severity.ERROR, message="x"))
        assert r.score <= 60
        assert "Poor" in r.score_label or "Not" in r.score_label

    def test_to_dict(self):
        r = ManufacturingReport()
        r.add_issue(ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL, severity=Severity.WARNING,
            message="QR small", suggestion="Increase QR",
        ))
        d = r.to_dict()
        assert d["score"] > 0
        assert len(d["issues"]) == 1
        assert d["suggestions"] == ["Increase QR"]

    def test_fixes(self):
        r = ManufacturingReport()
        r.fixes.append(ManufacturingFix(node_id="qr1", description="Increase QR", action="increase_size", suggested_value=24))
        assert len(r.fixes) == 1
        assert r.fixes[0].suggested_value == 24


class TestManufacturingFix:
    def test_fix_creation(self):
        fix = ManufacturingFix(
            node_id="qr1",
            description="Increase QR to 24mm",
            action="increase_size",
            suggested_value=24.0,
        )
        assert fix.node_id == "qr1"
        assert fix.action == "increase_size"
        assert fix.suggested_value == 24.0
