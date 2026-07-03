"""Tests for kernel QR, SVG color separation, and pattern tilings."""

import math

import pytest

from cardforge.kernel.qr import qr_cross_section, format_qr_payload
from cardforge.kernel.shapes2d import rounded_rect
from cardforge.kernel.svg import svg_to_color_shapes, SVGParseError
from cardforge.kernel import patterns


class TestQR:
    def test_area_equals_dark_modules(self):
        r = qr_cross_section("https://cardforge.dev", size_mm=24, quiet_zone_mm=2)
        dark = round(r.cross_section.area() / (r.module_mm ** 2))
        total = r.modules ** 2
        assert 0.35 * total < dark < 0.65 * total, "dark module ratio sane"
        assert r.total_mm == pytest.approx(28)

    def test_anchor_and_quiet_zone(self):
        r = qr_cross_section("test", size_mm=20, quiet_zone_mm=3)
        min_x, min_y, max_x, max_y = r.cross_section.bounds()
        assert min_x >= 3 - 1e-6 and max_x <= 23 + 1e-6
        assert max_y <= -3 + 1e-6 and min_y >= -23 - 1e-6

    def test_payload_formats(self):
        assert format_qr_payload("url", {"url": "https://x.dev"}) == "https://x.dev"
        assert format_qr_payload("wifi", {
            "wifi_ssid": "Net", "wifi_password": "pw"}) == "WIFI:T:WPA;S:Net;P:pw;;"
        assert format_qr_payload("email", {
            "email_address": "a@b.c", "email_subject": "Hi"}) == "mailto:a@b.c?subject=Hi"
        vcard = format_qr_payload("vcard", {"vcard_name": "Ada"})
        assert "BEGIN:VCARD" in vcard and "FN:Ada" in vcard

    def test_empty_payload_raises(self):
        with pytest.raises(ValueError):
            qr_cross_section("", 24)


class TestSVG:
    TWO_COLOR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10">
      <rect x="0" y="0" width="10" height="10" fill="#ff0000"/>
      <g transform="translate(10,0)"><circle cx="5" cy="5" r="5" fill="#0000ff"/></g>
    </svg>"""

    def test_two_colors_separated(self):
        shapes = svg_to_color_shapes(self.TWO_COLOR, target_width=20)
        assert sorted(shapes.keys()) == ["#0000ff", "#ff0000"]
        assert shapes["#ff0000"].area() == pytest.approx(100, rel=0.02)
        assert shapes["#0000ff"].area() == pytest.approx(math.pi * 25, rel=0.02)

    def test_transform_applied_and_scaled(self):
        shapes = svg_to_color_shapes(self.TWO_COLOR, target_width=40)  # 2x scale
        min_x, _, max_x, _ = shapes["#0000ff"].bounds()
        assert min_x == pytest.approx(20, abs=0.5)
        assert max_x == pytest.approx(40, abs=0.5)

    def test_y_flip_to_local_space(self):
        shapes = svg_to_color_shapes(self.TWO_COLOR, target_width=20)
        _, min_y, _, max_y = shapes["#ff0000"].bounds()
        assert max_y <= 1e-6 and min_y >= -10 - 1e-6

    def test_fill_none_skipped(self):
        svg = '<svg viewBox="0 0 10 10"><rect width="10" height="10" fill="none"/></svg>'
        assert svg_to_color_shapes(svg, 10) == {}

    def test_invalid_svg_raises(self):
        with pytest.raises(SVGParseError):
            svg_to_color_shapes("not xml at all <<<", 10)


class TestPatterns:
    REGION = rounded_rect(40, 20, 2)

    def test_dots_clipped_to_region(self):
        cs = patterns.dots(self.REGION, spacing=4, dot_diameter=1.5)
        assert 0 < cs.area() < self.REGION.area()
        rb, pb = self.REGION.bounds(), cs.bounds()
        assert pb[0] >= rb[0] - 1e-6 and pb[2] <= rb[2] + 1e-6

    def test_lines_density_scales_with_spacing(self):
        sparse = patterns.lines(self.REGION, spacing=8, line_width=0.8).area()
        dense = patterns.lines(self.REGION, spacing=4, line_width=0.8).area()
        assert dense > sparse * 1.6

    def test_grid_denser_than_lines(self):
        l = patterns.lines(self.REGION, 5, 0.8).area()
        g = patterns.grid(self.REGION, 5, 0.8).area()
        assert g > l * 1.5

    def test_hex_three_families(self):
        h = patterns.hex_grid(self.REGION, 6, 0.6)
        assert h.area() > patterns.lines(self.REGION, 6, 0.6).area() * 2

    def test_repeat_shape_tiles_unit(self):
        from cardforge.kernel.shapes2d import rect
        unit = rect(2, 1)
        cs = patterns.repeat_shape(self.REGION, unit, spacing=6, angle_deg=-25)
        assert cs.area() > unit.area() * 8, "many tiles must survive clipping"
        assert cs.area() < self.REGION.area()
