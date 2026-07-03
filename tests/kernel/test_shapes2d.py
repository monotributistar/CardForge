"""Tests for kernel 2D primitives — analytic area checks and placement."""

import math

import pytest

from cardforge.kernel.shapes2d import (
    rect, rounded_rect, circle, ring, frame, corner_marks, svg_path,
    place, bounds_of,
)


class TestPrimitives:
    def test_rect_area_and_anchor(self):
        cs = rect(10, 5)
        assert cs.area() == pytest.approx(50)
        assert bounds_of(cs) == pytest.approx((0, -5, 10, 0))

    def test_rounded_rect_area_analytic(self):
        # area = w·h − (4 − π)·r²
        cs = rounded_rect(85, 54, 4)
        analytic = 85 * 54 - (4 - math.pi) * 16
        assert cs.area() == pytest.approx(analytic, rel=0.005)

    def test_rounded_rect_zero_radius_is_rect(self):
        assert rounded_rect(10, 5, 0).area() == pytest.approx(50)

    def test_rounded_rect_radius_clamped(self):
        # radius larger than half-height must clamp, not self-intersect
        cs = rounded_rect(20, 6, 10)
        assert 0 < cs.area() < 120

    def test_circle_area_analytic(self):
        cs = circle(10)
        assert cs.area() == pytest.approx(math.pi * 25, rel=0.005)
        assert bounds_of(cs) == pytest.approx((0, -10, 10, 0), abs=0.01)

    def test_ring_area(self):
        cs = ring(10, 2)  # outer r=5, inner r=3
        assert cs.area() == pytest.approx(math.pi * (25 - 9), rel=0.005)

    def test_frame_area(self):
        cs = frame(20, 10, 1)
        # band area = outer − inner = 200 − 18·8 = 56
        assert cs.area() == pytest.approx(56, rel=0.005)

    def test_corner_marks_area(self):
        cs = corner_marks(85, 54, 6, 1)
        # 4 L-shapes: each 6·1 + 1·6 − 1·1 = 11
        assert cs.area() == pytest.approx(44)

    def test_svg_path_triangle(self):
        cs = svg_path("M0,0 L10,0 L5,10 Z", target_width=10)
        assert cs.area() == pytest.approx(50, rel=0.02)
        # y-up: triangle hangs below anchor
        _, min_y, _, max_y = bounds_of(cs)
        assert min_y == pytest.approx(-10, abs=0.1)
        assert max_y == pytest.approx(0, abs=0.1)


class TestPlacement:
    def test_place_translates(self):
        cs = place(rect(4, 2), 10, 20)
        assert bounds_of(cs) == pytest.approx((10, 18, 14, 20))

    def test_place_rotates_around_anchor(self):
        cs = place(rect(4, 2), 10, 20, rotation_deg=90)
        # 90° CCW around anchor: content x∈[0,4],y∈[-2,0] → x∈[0,2],y∈[0,4]
        assert bounds_of(cs) == pytest.approx((10, 20, 12, 24), abs=1e-6)

    def test_place_scales(self):
        cs = place(rect(4, 2), 0, 0, scale=2.0)
        assert cs.area() == pytest.approx(32)
