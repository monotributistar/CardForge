"""Tests for export paths."""

from pathlib import Path
from cardforge.export.paths import prepare_export_paths, sanitize_project_name, ExportPaths


class TestSanitizeProjectName:
    def test_replaces_spaces(self):
        assert sanitize_project_name("Javier Business Card") == "Javier_Business_Card"

    def test_replaces_special_chars(self):
        assert sanitize_project_name("test!@#card") == "test_card"

    def test_collapses_underscores(self):
        assert sanitize_project_name("a   b") == "a_b"

    def test_empty_returns_unnamed(self):
        assert sanitize_project_name("!!!") == "unnamed"

    def test_plain_name_unchanged(self):
        assert sanitize_project_name("test_card") == "test_card"


class TestExportPaths:
    def test_creates_all_directories(self, tmp_path):
        paths = prepare_export_paths("Test Card", base_dir=tmp_path)
        assert paths.root.exists()
        assert paths.assets_dir.exists()
        assert paths.preview_dir.exists()
        assert paths.scad_dir.exists()
        assert paths.stl_dir.exists()
        assert paths.stl_parts_dir.exists()
        assert paths.three_mf_dir.exists()

    def test_root_is_sanitized(self, tmp_path):
        paths = prepare_export_paths("Javier Business Card", base_dir=tmp_path)
        assert paths.root.name == "Javier_Business_Card"

    def test_idempotent(self, tmp_path):
        paths1 = prepare_export_paths("Test", base_dir=tmp_path)
        paths2 = prepare_export_paths("Test", base_dir=tmp_path)
        assert paths1.root == paths2.root

    def test_path_types(self, tmp_path):
        paths = prepare_export_paths("Test", base_dir=tmp_path)
        assert isinstance(paths, ExportPaths)
        assert isinstance(paths.assets_dir, Path)
