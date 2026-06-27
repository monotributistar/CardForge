"""Tests for Transform and Constraints."""

import pytest
from cardforge.domain.transform import Transform
from cardforge.domain.geometry import Position, Bounds, Severity
from cardforge.domain.constraints import (
    ConstraintIssue,
    ConstraintResult,
    check_min_feature_size,
    check_inside_face_bounds,
    check_no_overlap,
    check_qr_min_size,
    check_qr_quiet_zone,
    check_safe_margin,
)


class TestTransform:
    def test_default_transform(self):
        t = Transform()
        assert t.position.x == 0.0
        assert t.position.y == 0.0
        assert t.rotation == 0.0
        assert t.scale_x == 1.0
        assert t.scale_y == 1.0

    def test_custom_transform(self):
        t = Transform(
            position=Position(10, 20),
            rotation=45,
            scale_x=2.0,
            scale_y=0.5,
        )
        assert t.position.x == 10
        assert t.position.y == 20
        assert t.rotation == 45
        assert t.scale_x == 2.0
        assert t.scale_y == 0.5

    def test_to_dict(self):
        t = Transform(position=Position(5, 3), rotation=90, scale_x=1.5, scale_y=1.0)
        d = t.to_dict()
        assert d["position"] == {"x": 5, "y": 3}
        assert d["rotation"] == 90
        assert d["scale_x"] == 1.5
        assert d["scale_y"] == 1.0


class TestConstraintIssue:
    def test_error_severity(self):
        issue = ConstraintIssue(severity=Severity.ERROR, message="bad")
        assert issue.is_error
        assert not issue.is_warning

    def test_warning_severity(self):
        issue = ConstraintIssue(severity=Severity.WARNING, message="meh")
        assert issue.is_warning
        assert not issue.is_error


class TestConstraintResult:
    def test_empty_result(self):
        r = ConstraintResult()
        assert not r.has_errors
        assert not r.has_warnings
        assert r.errors == []
        assert r.warnings == []

    def test_mixed_issues(self):
        r = ConstraintResult()
        r.add(ConstraintIssue(Severity.ERROR, "critical"))
        r.add(ConstraintIssue(Severity.WARNING, "minor"))
        assert r.has_errors
        assert r.has_warnings
        assert len(r.errors) == 1
        assert len(r.warnings) == 1


class TestMinFeatureSize:
    def test_too_small_width(self):
        issues = check_min_feature_size(Bounds(0, 0, 0.3, 5), "feat1")
        assert len(issues) == 1
        assert issues[0].is_error
        assert "width" in issues[0].message.lower()

    def test_too_small_height(self):
        issues = check_min_feature_size(Bounds(0, 0, 5, 0.3), "feat1")
        assert len(issues) == 1
        assert "height" in issues[0].message.lower()

    def test_fine_size(self):
        issues = check_min_feature_size(Bounds(0, 0, 10, 10), "feat1")
        assert len(issues) == 0


class TestInsideFaceBounds:
    def test_inside(self):
        face = Bounds(0, 0, 100, 100)
        feat = Bounds(10, 10, 50, 50)
        issues = check_inside_face_bounds(feat, face, "f1", "face")
        assert len(issues) == 0

    def test_outside_right(self):
        face = Bounds(0, 0, 100, 100)
        feat = Bounds(90, 10, 30, 50)  # extends to 120 > 100
        issues = check_inside_face_bounds(feat, face, "f1", "face")
        assert len(issues) == 1
        assert issues[0].is_error


class TestNoOverlap:
    def test_no_overlap(self):
        a = Bounds(0, 0, 10, 10)
        b = Bounds(20, 20, 10, 10)
        issues = check_no_overlap(a, b, "a", "b")
        assert len(issues) == 0

    def test_overlap(self):
        a = Bounds(0, 0, 20, 20)
        b = Bounds(10, 10, 20, 20)
        issues = check_no_overlap(a, b, "a", "b")
        assert len(issues) == 1
        assert issues[0].is_warning


class TestQRConstraints:
    def test_qr_too_small(self):
        issues = check_qr_min_size(15, "qr1")
        assert len(issues) == 1
        assert issues[0].is_warning

    def test_qr_ok(self):
        issues = check_qr_min_size(24, "qr1")
        assert len(issues) == 0

    def test_quiet_zone_ok(self):
        face = Bounds(0, 0, 100, 100)
        qr = Bounds(10, 10, 24, 24)
        issues = check_qr_quiet_zone(qr, face, "qr1")
        assert len(issues) == 0

    def test_quiet_zone_too_close_left(self):
        face = Bounds(0, 0, 100, 100)
        qr = Bounds(1, 10, 24, 24)  # 1mm from left < 2mm
        issues = check_qr_quiet_zone(qr, face, "qr1")
        assert len(issues) >= 1


class TestSafeMargin:
    def test_within_margin(self):
        face = Bounds(0, 0, 100, 100)
        feat = Bounds(20, 20, 60, 60)
        issues = check_safe_margin(feat, face, "f1", margin=1.0)
        assert len(issues) == 0

    def test_too_close_left(self):
        face = Bounds(0, 0, 100, 100)
        feat = Bounds(0.5, 20, 50, 50)  # 0.5mm < 1.0mm margin
        issues = check_safe_margin(feat, face, "f1", margin=1.0)
        assert len(issues) == 1
