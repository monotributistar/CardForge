"""Tests for manufacturing pipeline stage and ExportPaths reports_dir."""

import pytest
from cardforge.export.paths import prepare_export_paths
from cardforge.pipeline.stages import manufacturing_analysis_stage, _get_profile
from cardforge.manufacturing.profiles import ManufacturingProfile
from cardforge.geometry_ir.nodes import DocumentNode


class TestExportPathsReportsDir:
    def test_reports_dir_created(self, tmp_path):
        paths = prepare_export_paths("Test", base_dir=tmp_path)
        assert paths.reports_dir.exists()

    def test_reports_dir_is_path(self, tmp_path):
        paths = prepare_export_paths("Test", base_dir=tmp_path)
        assert "reports" in str(paths.reports_dir)


class TestGetProfile:
    def test_fdm_standard(self):
        p = _get_profile("fdm-standard")
        assert p.process == "fdm"
        assert p.nozzle == 0.4

    def test_fdm_fine(self):
        p = _get_profile("fdm-fine")
        assert p.nozzle == 0.25

    def test_sla(self):
        p = _get_profile("sla")
        assert p.process == "sla"

    def test_unknown_defaults_to_fdm(self):
        p = _get_profile("nonexistent")
        assert p.process == "fdm"


class TestManufacturingStage:
    def test_stage_requires_document(self):
        ctx = {}
        result = manufacturing_analysis_stage(ctx)
        assert result.status == "error"
        assert "geometry_document" in result.message

    def test_stage_with_clean_document(self, tmp_path):
        doc = DocumentNode(id="doc", name="Test")
        paths = prepare_export_paths("Test", base_dir=tmp_path)
        ctx = {
            "geometry_document": doc,
            "export_paths": paths,
            "manufacturing_profile": "fdm-standard",
        }
        result = manufacturing_analysis_stage(ctx)
        assert result.status == "ok"
        assert "Score" in result.message

    def test_stage_with_errors_blocks(self, tmp_path):
        from cardforge.geometry_ir.nodes import SVGNode

        svg = SVGNode(id="qr_code", file_path="qr.svg", width=10, height=10)
        doc = DocumentNode(id="doc", name="Bad", children=[svg])
        paths = prepare_export_paths("Test", base_dir=tmp_path)
        ctx = {
            "geometry_document": doc,
            "export_paths": paths,
            "manufacturing_profile": "fdm-standard",
        }
        result = manufacturing_analysis_stage(ctx)
        assert result.status == "error"

    def test_stage_with_ignore_errors_passes(self, tmp_path):
        from cardforge.geometry_ir.nodes import SVGNode

        svg = SVGNode(id="qr_code", file_path="qr.svg", width=10, height=10)
        doc = DocumentNode(id="doc", name="Bad", children=[svg])
        paths = prepare_export_paths("Test", base_dir=tmp_path)
        ctx = {
            "geometry_document": doc,
            "export_paths": paths,
            "manufacturing_profile": "fdm-standard",
            "ignore_manufacturing_errors": True,
        }
        result = manufacturing_analysis_stage(ctx)
        assert result.status == "ok"

    def test_stage_exports_reports(self, tmp_path):
        doc = DocumentNode(id="doc", name="Test")
        paths = prepare_export_paths("Test", base_dir=tmp_path)
        ctx = {
            "geometry_document": doc,
            "export_paths": paths,
            "manufacturing_profile": "fdm-standard",
        }
        manufacturing_analysis_stage(ctx)
        assert ctx.get("report_json_path") is not None
        assert ctx["report_json_path"].exists()
        assert ctx["report_md_path"].exists()
