"""Tests for manufacturing report exporter and formatter."""

import json
import pytest
from cardforge.manufacturing.export_report import export_report_json, export_report_markdown
from cardforge.manufacturing.formatter import format_report_console
from cardforge.manufacturing.report import ManufacturingReport
from cardforge.manufacturing.issues import ManufacturingIssue, IssueCode, Severity
from cardforge.manufacturing.profiles import ManufacturingProfile


class TestExportReportJson:
    def test_exports_json_file(self, tmp_path):
        report = ManufacturingReport()
        out = tmp_path / "report.json"
        result = export_report_json(report, out)
        assert result == out
        assert out.exists()

    def test_json_contains_score(self, tmp_path):
        report = ManufacturingReport()
        out = tmp_path / "report.json"
        export_report_json(report, out)
        data = json.loads(out.read_text())
        assert data["score"] == 100

    def test_json_with_issues(self, tmp_path):
        report = ManufacturingReport()
        report.add_issue(ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL, severity=Severity.ERROR,
            message="QR too small",
            suggestion="Increase QR",
        ))
        out = tmp_path / "report.json"
        export_report_json(report, out)
        data = json.loads(out.read_text())
        assert len(data["issues"]) == 1
        assert data["issues"][0]["code"] == "qr_too_small"
        assert data["suggestions"] == ["Increase QR"]

    def test_json_contains_metrics(self, tmp_path):
        report = ManufacturingReport()
        report.metrics.feature_count = 5
        out = tmp_path / "report.json"
        export_report_json(report, out)
        data = json.loads(out.read_text())
        assert data["metrics"]["feature_count"] == 5

    def test_json_contains_profile(self, tmp_path):
        report = ManufacturingReport(profile=ManufacturingProfile.fdm_standard())
        out = tmp_path / "report.json"
        export_report_json(report, out)
        data = json.loads(out.read_text())
        assert data["profile"]["process"] == "fdm"

    def test_creates_parent_dirs(self, tmp_path):
        report = ManufacturingReport()
        out = tmp_path / "deep" / "nested" / "report.json"
        export_report_json(report, out)
        assert out.exists()


class TestExportReportMarkdown:
    def test_exports_md_file(self, tmp_path):
        report = ManufacturingReport()
        out = tmp_path / "report.md"
        result = export_report_markdown(report, out)
        assert result == out
        assert out.exists()

    def test_md_contains_score(self, tmp_path):
        report = ManufacturingReport()
        out = tmp_path / "report.md"
        export_report_markdown(report, out)
        content = out.read_text()
        assert "100/100" in content

    def test_md_with_warnings(self, tmp_path):
        report = ManufacturingReport()
        report.add_issue(ManufacturingIssue(
            code=IssueCode.MIN_EMBOSS, severity=Severity.WARNING,
            message="Emboss too low", suggestion="Increase to 0.4mm",
        ))
        out = tmp_path / "report.md"
        export_report_markdown(report, out)
        content = out.read_text()
        assert "Emboss too low" in content
        assert "Increase to 0.4mm" in content

    def test_md_not_manufacturable(self, tmp_path):
        report = ManufacturingReport()
        report.add_issue(ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL, severity=Severity.ERROR,
            message="QR too small",
        ))
        out = tmp_path / "report.md"
        export_report_markdown(report, out)
        content = out.read_text()
        assert "Not manufacturable" in content


class TestFormatter:
    def test_formats_clean_report(self):
        report = ManufacturingReport()
        result = format_report_console(report)
        assert "Manufacturing Analysis" in result
        assert "100/100" in result
        assert "Manufacturable" in result

    def test_formats_with_warnings(self):
        report = ManufacturingReport()
        report.add_issue(ManufacturingIssue(
            code=IssueCode.MIN_EMBOSS, severity=Severity.WARNING,
            message="Emboss too low", suggestion="Increase emboss",
        ))
        result = format_report_console(report)
        assert "Warnings:" in result
        assert "Emboss too low" in result
        assert "Suggestions:" in result
        assert "Increase emboss" in result

    def test_formats_with_errors(self):
        report = ManufacturingReport()
        report.add_issue(ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL, severity=Severity.ERROR,
            message="QR too small",
        ))
        result = format_report_console(report)
        assert "Errors:" in result
        assert "Not manufacturable" in result
        assert "Build blocked" in result

    def test_formats_profile_info(self):
        report = ManufacturingReport(profile=ManufacturingProfile.fdm_standard())
        result = format_report_console(report)
        assert "Generic FDM" in result
        assert "PLA" in result
