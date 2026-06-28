"""Tests for manufacturing profiles, issues, and rules."""

import pytest
from cardforge.manufacturing.profiles import ManufacturingProfile
from cardforge.manufacturing.issues import ManufacturingIssue, IssueCode, Severity
from cardforge.manufacturing.rules import (
    check_line_width, check_wall_thickness,
    check_emboss_height, check_deboss_depth,
    check_qr_size, check_qr_module_size,
    check_text_size, check_gap, check_unsupported_relief,
)


class TestManufacturingProfile:
    def test_fdm_standard_defaults(self):
        p = ManufacturingProfile.fdm_standard()
        assert p.process == "fdm"
        assert p.nozzle == 0.4
        assert p.min_line_width == 0.4
        assert p.min_emboss == 0.3

    def test_fdm_fine_defaults(self):
        p = ManufacturingProfile.fdm_fine()
        assert p.nozzle == 0.25
        assert p.min_line_width == 0.25

    def test_sla_profile(self):
        p = ManufacturingProfile.sla_standard()
        assert p.process == "sla"
        assert p.nozzle == 0.0

    def test_profile_to_dict(self):
        p = ManufacturingProfile.fdm_standard()
        d = p.to_dict()
        assert d["process"] == "fdm"
        assert "min_line_width" in d


class TestManufacturingIssue:
    def test_issue_creation(self):
        issue = ManufacturingIssue(
            code=IssueCode.MIN_LINE_WIDTH,
            severity=Severity.ERROR,
            message="Line too thin",
            node_id="rect1",
            value=0.3,
            threshold=0.4,
        )
        assert issue.code == IssueCode.MIN_LINE_WIDTH
        assert issue.severity == Severity.ERROR
        assert issue.value == 0.3

    def test_issue_to_dict(self):
        issue = ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL,
            severity=Severity.WARNING,
            message="QR too small",
            suggestion="Increase QR to 24mm",
        )
        d = issue.to_dict()
        assert d["code"] == "qr_too_small"
        assert d["suggestion"] == "Increase QR to 24mm"


class TestRules:
    def _profile(self):
        return ManufacturingProfile.fdm_standard()

    def test_line_width_ok(self):
        issues = check_line_width(0.6, 10, "r1", self._profile())
        assert len(issues) == 0

    def test_line_width_too_thin(self):
        issues = check_line_width(0.3, 10, "r1", self._profile())
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_wall_ok(self):
        issues = check_wall_thickness(1.0, "w1", self._profile())
        assert len(issues) == 0

    def test_wall_too_thin(self):
        issues = check_wall_thickness(0.5, "w1", self._profile())
        assert len(issues) == 1

    def test_emboss_ok(self):
        issues = check_emboss_height(0.4, "e1", self._profile())
        assert len(issues) == 0

    def test_emboss_too_low(self):
        issues = check_emboss_height(0.2, "e1", self._profile())
        assert len(issues) == 1

    def test_deboss_ok(self):
        issues = check_deboss_depth(0.3, "d1", self._profile())
        assert len(issues) == 0

    def test_deboss_too_shallow(self):
        issues = check_deboss_depth(0.1, "d1", self._profile())
        assert len(issues) == 1

    def test_qr_size_ok(self):
        issues = check_qr_size(24, "qr1", self._profile())
        assert len(issues) == 0

    def test_qr_too_small(self):
        issues = check_qr_size(15, "qr1", self._profile())
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_qr_module_ok(self):
        issues = check_qr_module_size(24, "qr1", self._profile())
        assert len(issues) == 0

    def test_qr_module_too_small(self):
        # 15mm QR with 33 modules = 0.45mm per module < 0.6mm min
        issues = check_qr_module_size(15, "qr1", self._profile())
        assert len(issues) == 1

    def test_text_ok(self):
        issues = check_text_size(3.5, "t1", self._profile())
        assert len(issues) == 0

    def test_text_too_small(self):
        issues = check_text_size(2.0, "t1", self._profile())
        assert len(issues) == 1

    def test_gap_ok(self):
        issues = check_gap(0.8, "g1", self._profile())
        assert len(issues) == 0

    def test_gap_too_small(self):
        issues = check_gap(0.3, "g1", self._profile())
        assert len(issues) == 1

    def test_unsupported_relief_emboss_ok(self):
        issues = check_unsupported_relief("emboss", "r1", self._profile())
        assert len(issues) == 0

    def test_unsupported_relief_unknown(self):
        p = ManufacturingProfile.fdm_standard()
        p.supported_relief_modes = ["flush"]
        issues = check_unsupported_relief("emboss", "r1", p)
        assert len(issues) == 1
