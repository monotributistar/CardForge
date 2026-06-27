"""Tests for pattern generator."""

import pytest
from cardforge.assets.patterns import generate_text_repeat_pattern_svg


class TestPatternGenerator:
    def test_generates_svg_file(self, tmp_path):
        out = tmp_path / "pattern.svg"
        result = generate_text_repeat_pattern_svg("JR", out, 85, 54, spacing_mm=10)
        assert result == out
        assert out.exists()
        content = out.read_text()
        assert "<svg" in content
        assert "</svg>" in content

    def test_contains_repeated_text(self, tmp_path):
        out = tmp_path / "pattern.svg"
        generate_text_repeat_pattern_svg("JR", out, 85, 54, spacing_mm=10)
        content = out.read_text()
        # Should have multiple text occurrences
        count = content.count(">JR<")
        assert count > 1

    def test_respects_width_height(self, tmp_path):
        out = tmp_path / "pattern.svg"
        generate_text_repeat_pattern_svg("X", out, 85, 54)
        content = out.read_text()
        assert 'width="85mm"' in content
        assert 'height="54mm"' in content

    def test_empty_text_raises(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            generate_text_repeat_pattern_svg("", tmp_path / "p.svg", 85, 54)

    def test_whitespace_text_raises(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            generate_text_repeat_pattern_svg("  ", tmp_path / "p.svg", 85, 54)

    def test_zero_spacing_raises(self, tmp_path):
        with pytest.raises(ValueError, match="spacing_mm"):
            generate_text_repeat_pattern_svg("X", tmp_path / "p.svg", 85, 54, spacing_mm=0)

    def test_negative_spacing_raises(self, tmp_path):
        with pytest.raises(ValueError, match="spacing_mm"):
            generate_text_repeat_pattern_svg("X", tmp_path / "p.svg", 85, 54, spacing_mm=-1)

    def test_rotation_appears_in_transform(self, tmp_path):
        out = tmp_path / "pattern.svg"
        generate_text_repeat_pattern_svg("JR", out, 85, 54, rotation_deg=-25)
        content = out.read_text()
        assert 'rotate(-25' in content

    def test_custom_color(self, tmp_path):
        out = tmp_path / "pattern.svg"
        generate_text_repeat_pattern_svg("X", out, 85, 54, color="#ff0000")
        content = out.read_text()
        assert '#ff0000' in content

    def test_opacity_applied(self, tmp_path):
        out = tmp_path / "pattern.svg"
        generate_text_repeat_pattern_svg("X", out, 85, 54, opacity=0.5)
        content = out.read_text()
        assert 'opacity="0.5"' in content

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "deep" / "pattern.svg"
        generate_text_repeat_pattern_svg("X", out, 85, 54)
        assert out.exists()
