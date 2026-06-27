"""Tests for QR generator and vCard builder."""

import pytest
from pathlib import Path
from cardforge.assets.qr import generate_qr_svg, QRGenerationError, VALID_ERROR_CORRECTION
from cardforge.assets.vcard import build_vcard


class TestVCard:
    def test_builds_basic_vcard(self):
        owner = {
            "name": "Javier Rodriguez",
            "title": "Frontend Developer",
            "email": "javier@example.com",
        }
        vcard = build_vcard(owner)
        assert "BEGIN:VCARD" in vcard
        assert "VERSION:3.0" in vcard
        assert "FN:Javier Rodriguez" in vcard
        assert "TITLE:Frontend Developer" in vcard
        assert "EMAIL:javier@example.com" in vcard
        assert "END:VCARD" in vcard

    def test_includes_optional_fields(self):
        owner = {
            "name": "Test",
            "website": "https://example.com",
            "github": "https://github.com/test",
            "linkedin": "https://linkedin.com/in/test",
        }
        vcard = build_vcard(owner)
        assert "URL:https://example.com" in vcard
        assert "NOTE:GitHub:" in vcard
        assert "NOTE:LinkedIn:" in vcard

    def test_minimal_owner(self):
        vcard = build_vcard({"name": "Min"})
        assert "FN:Min" in vcard


class TestQRGenerator:
    def test_generates_svg_file(self, tmp_path):
        out = tmp_path / "qr.svg"
        result = generate_qr_svg("https://example.com", out)
        assert result == out
        assert out.exists()
        content = out.read_text()
        assert "<svg" in content
        assert "<rect" in content

    def test_svg_has_correct_dimensions(self, tmp_path):
        out = tmp_path / "qr.svg"
        generate_qr_svg("test", out, size_mm=24, quiet_zone_mm=2)
        content = out.read_text()
        assert 'width="28mm"' in content  # 24 + 2*2
        assert 'height="28mm"' in content

    def test_empty_value_raises(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            generate_qr_svg("", tmp_path / "qr.svg")

    def test_whitespace_only_raises(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            generate_qr_svg("   ", tmp_path / "qr.svg")

    def test_zero_size_raises(self, tmp_path):
        with pytest.raises(ValueError, match="size_mm"):
            generate_qr_svg("test", tmp_path / "qr.svg", size_mm=0)

    def test_negative_quiet_zone_raises(self, tmp_path):
        with pytest.raises(ValueError, match="quiet_zone_mm"):
            generate_qr_svg("test", tmp_path / "qr.svg", quiet_zone_mm=-1)

    def test_invalid_error_correction_raises(self, tmp_path):
        with pytest.raises(ValueError, match="error_correction"):
            generate_qr_svg("test", tmp_path / "qr.svg", error_correction="X")

    def test_all_valid_error_corrections(self):
        for ec in VALID_ERROR_CORRECTION:
            assert ec in ("L", "M", "Q", "H")

    def test_generates_vcard_qr(self, tmp_path):
        vcard = build_vcard({
            "name": "Javier",
            "email": "j@test.com",
        })
        out = tmp_path / "vcard_qr.svg"
        generate_qr_svg(vcard, out)
        content = out.read_text()
        assert "<svg" in content

    def test_generates_url_qr(self, tmp_path):
        out = tmp_path / "url_qr.svg"
        generate_qr_svg("https://github.com/monotributistar", out)
        content = out.read_text()
        assert "<svg" in content

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "deep" / "nested" / "qr.svg"
        generate_qr_svg("test", out)
        assert out.exists()
