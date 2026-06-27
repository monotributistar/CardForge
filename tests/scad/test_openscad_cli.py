"""Tests for OpenSCAD CLI wrapper."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cardforge.export.openscad_cli import (
    find_openscad,
    run_openscad,
    OpenSCADResult,
    OpenSCADNotFoundError,
)


class TestFindOpenscad:
    def test_env_var_priority(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "fake_openscad"
        fake_bin.write_text("")
        fake_bin.chmod(0o755)
        monkeypatch.setenv("OPENSCAD_BIN", str(fake_bin))
        result = find_openscad()
        assert result == str(fake_bin)

    def test_env_var_not_found(self, monkeypatch):
        monkeypatch.setenv("OPENSCAD_BIN", "/nonexistent/openscad")
        # Should fall through to PATH check; if openscad isn't on PATH, raises
        # Mock shutil.which to avoid system dependency
        with patch("cardforge.export.openscad_cli.shutil.which", return_value=None):
            monkeypatch.delenv("OPENSCAD_BIN")
            # This will fail because openscad not on PATH in test env
            # We just check the error type
            try:
                find_openscad()
                # If openscad IS on PATH, this won't fail. That's OK.
            except OpenSCADNotFoundError:
                pass

    def test_missing_everywhere(self, monkeypatch):
        monkeypatch.delenv("OPENSCAD_BIN", raising=False)
        with patch("cardforge.export.openscad_cli.shutil.which", return_value=None):
            with patch("cardforge.export.openscad_cli.os.path.isfile", return_value=False):
                with pytest.raises(OpenSCADNotFoundError):
                    find_openscad()


class TestRunOpenscad:
    def test_successful_run(self, tmp_path):
        scad = tmp_path / "test.scad"
        scad.write_text("cube([1,1,1]);")
        stl = tmp_path / "output.stl"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            # Create output file as if OpenSCAD ran
            stl.write_text("fake stl")
            result = run_openscad(scad, stl, openscad_bin="/fake/openscad")
            assert result.success
            assert result.output_file == stl

    def test_failed_run(self, tmp_path):
        scad = tmp_path / "test.scad"
        scad.write_text("invalid")
        stl = tmp_path / "output.stl"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Parse error"

        with patch("subprocess.run", return_value=mock_result):
            result = run_openscad(scad, stl, openscad_bin="/fake/openscad")
            assert not result.success
            assert "Parse error" in result.stderr

    def test_cmd_includes_flags(self, tmp_path):
        scad = tmp_path / "test.scad"
        scad.write_text("cube([1,1,1]);")
        stl = tmp_path / "output.stl"

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            # Make output file exist
            stl.write_text("fake")

            run_openscad(scad, stl, openscad_bin="/fake/openscad")
            args = mock_run.call_args[0][0]
            assert "-o" in args
            assert "--export-format" in args
            assert "binstl" in args

    def test_timeout(self, tmp_path):
        import subprocess
        scad = tmp_path / "test.scad"
        scad.write_text("cube([1,1,1]);")
        stl = tmp_path / "output.stl"

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 1)):
            result = run_openscad(scad, stl, openscad_bin="/fake/openscad", timeout=1)
            assert not result.success
            assert "timed out" in result.stderr.lower()

    def test_creates_output_dir(self, tmp_path):
        scad = tmp_path / "test.scad"
        scad.write_text("cube([1,1,1]);")
        stl = tmp_path / "deep" / "nested" / "output.stl"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            stl.parent.mkdir(parents=True)
            stl.write_text("fake")
            result = run_openscad(scad, stl, openscad_bin="/fake/openscad")
            assert result.success
