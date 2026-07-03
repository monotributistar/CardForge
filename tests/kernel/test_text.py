"""Tests for text rendering — holes, kerning, variable fonts, alignment."""

import pytest

from cardforge.kernel.text import text_block

FAMILY = "Arial"  # static TTF present on macOS (fonts.py falls back if not)


class TestGlyphGeometry:
    def test_o_has_hole(self):
        r = text_block(["o"], FAMILY, 10.0)
        solid = r.cross_section.extrude(1.0)
        assert solid.genus() == 1, "the counter of 'o' must survive"

    def test_text_extrudes_to_valid_solid(self):
        r = text_block(["CardForge 123"], FAMILY, 4.0)
        solid = r.cross_section.extrude(0.4)
        assert solid.volume() > 0
        assert solid.num_tri() > 100

    def test_size_scales_area(self):
        small = text_block(["Hg"], FAMILY, 3.0).cross_section.area()
        big = text_block(["Hg"], FAMILY, 6.0).cross_section.area()
        assert big == pytest.approx(small * 4, rel=0.02), "area scales with size²"

    def test_empty_lines_produce_empty(self):
        r = text_block([""], FAMILY, 4.0)
        assert r.cross_section.is_empty()


class TestShaping:
    def test_kerning_applied(self):
        av = text_block(["AV"], FAMILY, 10.0).width
        a = text_block(["A"], FAMILY, 10.0).width
        v = text_block(["V"], FAMILY, 10.0).width
        assert av < a + v, "AV must be kerned tighter than A+V"


def _find_variable_family():
    """Discover a system variable font with a wght axis and latin glyphs."""
    from fontTools.ttLib import TTFont

    from cardforge.kernel.fonts import font_index

    for face in font_index().values():
        if not face.is_variable:
            continue
        try:
            f = TTFont(face.path, fontNumber=max(0, face.index), lazy=True)
            axes = {a.axisTag: (a.minValue, a.maxValue) for a in f["fvar"].axes}
            has_h = ord("H") in f.getBestCmap()
            f.close()
            wght = axes.get("wght")
            if has_h and wght and wght[0] <= 300 and wght[1] >= 700:
                return face.family
        except Exception:
            continue
    return None


class TestVariableFonts:
    def test_weight_axis_changes_area(self):
        family = _find_variable_family()
        if not family:
            pytest.skip("no variable font with wght axis on this system")
        light = text_block(["H"], family, 10.0, axes={"wght": 300})
        bold = text_block(["H"], family, 10.0, axes={"wght": 700})
        assert bold.cross_section.area() > light.cross_section.area() * 1.15

    def test_weight_param_sugar(self):
        family = _find_variable_family()
        if not family:
            pytest.skip("no variable font with wght axis on this system")
        w300 = text_block(["H"], family, 10.0, weight=300)
        w700 = text_block(["H"], family, 10.0, weight=700)
        assert w700.cross_section.area() > w300.cross_section.area() * 1.15


class TestBlockLayout:
    def test_multiline_stacks_downward(self):
        r = text_block(["AAA", "AAA"], FAMILY, 4.0, line_height=1.5)
        min_x, min_y, max_x, max_y = r.cross_section.bounds()
        assert max_y <= 0.01, "block hangs below its top-left anchor"
        assert min_y < -4.0, "second line extends further down"
        assert r.line_count == 2

    def test_align_center_and_right(self):
        left = text_block(["XXXX", "X"], FAMILY, 4.0, align="left")
        center = text_block(["XXXX", "X"], FAMILY, 4.0, align="center")
        right = text_block(["XXXX", "X"], FAMILY, 4.0, align="right")
        assert left.width == pytest.approx(center.width) == pytest.approx(right.width)
        # bounds identical (block box) but geometry differs by alignment
        assert left.cross_section.area() == pytest.approx(center.cross_section.area(), rel=1e-6)

    def test_fallback_family(self):
        r = text_block(["Hi"], "NoSuchFontFamily-XYZ", 4.0)
        assert not r.cross_section.is_empty(), "must fall back to a system font"
