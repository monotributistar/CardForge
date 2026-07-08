"""Tests for min_feature_width (nozzle-detail measurement)."""

import pytest

from cardforge.kernel.measure import min_feature_width
from cardforge.kernel.shapes2d import frame, rect, ring
from cardforge.kernel.text import text_block


class TestMinFeatureWidth:
    def test_thin_rect(self):
        assert min_feature_width(rect(20, 0.15)) == pytest.approx(0.15, abs=0.06)

    def test_thick_shape_caps(self):
        # a solid 10x10 pad has no thin detail → returns the hi cap
        assert min_feature_width(rect(10, 10)) == pytest.approx(2.0, abs=0.01)

    def test_frame_stroke(self):
        assert min_feature_width(frame(60, 40, 0.3)) == pytest.approx(0.3, abs=0.06)

    def test_ring_stroke(self):
        assert min_feature_width(ring(20, 0.5)) == pytest.approx(0.5, abs=0.08)

    def test_empty(self):
        from manifold3d import CrossSection
        assert min_feature_width(CrossSection()) == 0.0

    def test_detects_thin_text_strokes(self):
        # small text has strokes well under a 0.4mm nozzle
        w = min_feature_width(text_block(["Detalle"], "Arial", 3.0).cross_section)
        assert 0.1 < w < 0.4

    def test_width_invariant_to_transform(self):
        r = rect(20, 0.3)
        base = min_feature_width(r)
        moved = min_feature_width(r.translate((5, 9)).rotate(37).mirror((1, 0)))
        assert moved == pytest.approx(base, abs=0.03)

    def test_scale_changes_width(self):
        r = rect(20, 0.3)
        assert min_feature_width(r.scale((2, 2))) > min_feature_width(r) * 1.5

    def test_normal_text_at_readable_size_is_not_thin(self):
        """Regression: corner shedding on long text used to drag the
        estimate under the nozzle even when every stroke was thick.
        A size-10 sans block must measure well above a 0.4mm nozzle."""
        w = min_feature_width(
            text_block(["Monotributistar"], "DejaVu Sans", 10.0).cross_section)
        assert w > 0.55

    def test_corner_count_does_not_change_the_estimate(self):
        """Same stroke width, 10× the corners → same measurement."""
        one = min_feature_width(frame(20, 12, 0.5))
        many = min_feature_width(
            text_block(["mmmmmmmmmm"], "DejaVu Sans", 8.0).cross_section)
        # the text's true thinnest stroke at size 8 is ~0.6; the point is
        # that it stays in the same band as a lone 0.5mm frame instead of
        # collapsing toward zero with glyph count.
        assert many > one * 0.8
