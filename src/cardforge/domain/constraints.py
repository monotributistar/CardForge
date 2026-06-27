"""Constraints — domain-level validation rules for features and cards."""

from dataclasses import dataclass, field
from typing import List, Optional

from cardforge.domain.geometry import Severity, Bounds


@dataclass
class ConstraintIssue:
    """A single validation issue found during constraint checking."""

    severity: Severity
    message: str
    feature_id: Optional[str] = None
    face_id: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.severity == Severity.ERROR

    @property
    def is_warning(self) -> bool:
        return self.severity == Severity.WARNING


@dataclass
class ConstraintResult:
    """Result of running all constraints."""

    issues: List[ConstraintIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.is_error for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.is_warning for i in self.issues)

    @property
    def errors(self) -> List[ConstraintIssue]:
        return [i for i in self.issues if i.is_error]

    @property
    def warnings(self) -> List[ConstraintIssue]:
        return [i for i in self.issues if i.is_warning]

    def add(self, issue: ConstraintIssue) -> None:
        self.issues.append(issue)


# ── Constraint functions ──────────────────────────────────────────────────────


def check_min_feature_size(
    feature_bounds: Bounds,
    feature_id: str,
    min_width: float = 0.6,
    min_height: float = 0.6,
) -> List[ConstraintIssue]:
    """Check that a feature meets minimum printable size."""
    issues = []
    if feature_bounds.width < min_width:
        issues.append(ConstraintIssue(
            severity=Severity.ERROR,
            message=(
                f"Feature '{feature_id}' width ({feature_bounds.width} mm) "
                f"is below minimum ({min_width} mm)"
            ),
            feature_id=feature_id,
        ))
    if feature_bounds.height < min_height:
        issues.append(ConstraintIssue(
            severity=Severity.ERROR,
            message=(
                f"Feature '{feature_id}' height ({feature_bounds.height} mm) "
                f"is below minimum ({min_height} mm)"
            ),
            feature_id=feature_id,
        ))
    return issues


def check_inside_face_bounds(
    feature_bounds: Bounds,
    face_bounds: Bounds,
    feature_id: str,
    face_id: str,
) -> List[ConstraintIssue]:
    """Check that a feature is fully contained within its face."""
    issues = []
    if not face_bounds.contains(feature_bounds):
        issues.append(ConstraintIssue(
            severity=Severity.ERROR,
            message=(
                f"Feature '{feature_id}' extends outside face '{face_id}' bounds. "
                f"Feature: {feature_bounds.to_dict()}, Face: {face_bounds.to_dict()}"
            ),
            feature_id=feature_id,
            face_id=face_id,
        ))
    return issues


def check_no_overlap(
    bounds_a: Bounds,
    bounds_b: Bounds,
    feature_a_id: str,
    feature_b_id: str,
) -> List[ConstraintIssue]:
    """Check that two features don't overlap."""
    issues = []
    if bounds_a.intersects(bounds_b):
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=(
                f"Features '{feature_a_id}' and '{feature_b_id}' overlap"
            ),
            feature_id=feature_a_id,
        ))
    return issues


def check_qr_min_size(
    qr_size: float,
    feature_id: str,
    min_size: float = 22.0,
) -> List[ConstraintIssue]:
    """Check QR code meets minimum size for FDM 0.4mm nozzle."""
    issues = []
    if qr_size < min_size:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=(
                f"QR '{feature_id}' size ({qr_size} mm) is below recommended "
                f"minimum ({min_size} mm) for FDM 0.4mm nozzle"
            ),
            feature_id=feature_id,
        ))
    return issues


def check_qr_quiet_zone(
    qr_bounds: Bounds,
    face_bounds: Bounds,
    feature_id: str,
    quiet_zone: float = 2.0,
) -> List[ConstraintIssue]:
    """Check QR code has adequate quiet zone around it."""
    issues = []
    if qr_bounds.x < quiet_zone:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=f"QR '{feature_id}' lacks left quiet zone ({quiet_zone} mm)",
            feature_id=feature_id,
        ))
    if qr_bounds.y < quiet_zone:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=f"QR '{feature_id}' lacks top quiet zone ({quiet_zone} mm)",
            feature_id=feature_id,
        ))
    if face_bounds.right - qr_bounds.right < quiet_zone:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=f"QR '{feature_id}' lacks right quiet zone ({quiet_zone} mm)",
            feature_id=feature_id,
        ))
    if face_bounds.bottom - qr_bounds.bottom < quiet_zone:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=f"QR '{feature_id}' lacks bottom quiet zone ({quiet_zone} mm)",
            feature_id=feature_id,
        ))
    return issues


def check_safe_margin(
    feature_bounds: Bounds,
    face_bounds: Bounds,
    feature_id: str,
    margin: float = 1.0,
) -> List[ConstraintIssue]:
    """Check feature has safe margin from face edges."""
    issues = []
    if feature_bounds.x < margin:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=(
                f"Feature '{feature_id}' is too close to left edge "
                f"({feature_bounds.x} mm, margin is {margin} mm)"
            ),
            feature_id=feature_id,
        ))
    if feature_bounds.y < margin:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=(
                f"Feature '{feature_id}' is too close to top edge "
                f"({feature_bounds.y} mm, margin is {margin} mm)"
            ),
            feature_id=feature_id,
        ))
    if face_bounds.right - feature_bounds.right < margin:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=f"Feature '{feature_id}' is too close to right edge",
            feature_id=feature_id,
        ))
    if face_bounds.bottom - feature_bounds.bottom < margin:
        issues.append(ConstraintIssue(
            severity=Severity.WARNING,
            message=f"Feature '{feature_id}' is too close to bottom edge",
            feature_id=feature_id,
        ))
    return issues
