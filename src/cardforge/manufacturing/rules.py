"""Manufacturing rules — checks geometry against manufacturing profiles."""

from typing import List

from cardforge.manufacturing.profiles import ManufacturingProfile
from cardforge.manufacturing.issues import ManufacturingIssue, IssueCode, Severity


def check_line_width(
    width: float, height: float, node_id: str, profile: ManufacturingProfile,
) -> List[ManufacturingIssue]:
    """Check that a shape meets minimum line width."""
    issues = []
    if width < profile.min_line_width:
        issues.append(ManufacturingIssue(
            code=IssueCode.MIN_LINE_WIDTH, severity=Severity.ERROR,
            message=f"Line width {width:.2f}mm below minimum {profile.min_line_width}mm",
            node_id=node_id, value=width, threshold=profile.min_line_width,
            suggestion=f"Increase width to at least {profile.min_line_width}mm",
        ))
    return issues


def check_wall_thickness(
    width: float, node_id: str, profile: ManufacturingProfile,
) -> List[ManufacturingIssue]:
    """Check that a wall meets minimum thickness."""
    issues = []
    if width < profile.min_wall:
        issues.append(ManufacturingIssue(
            code=IssueCode.MIN_WALL_THICKNESS, severity=Severity.WARNING,
            message=f"Wall thickness {width:.2f}mm below minimum {profile.min_wall}mm",
            node_id=node_id, value=width, threshold=profile.min_wall,
            suggestion=f"Increase wall to at least {profile.min_wall}mm",
        ))
    return issues


def check_emboss_height(
    height: float, node_id: str, profile: ManufacturingProfile,
) -> List[ManufacturingIssue]:
    """Check emboss height is printable."""
    issues = []
    if height < profile.min_emboss:
        issues.append(ManufacturingIssue(
            code=IssueCode.MIN_EMBOSS, severity=Severity.WARNING,
            message=f"Emboss height {height:.2f}mm below minimum {profile.min_emboss}mm",
            node_id=node_id, value=height, threshold=profile.min_emboss,
            suggestion=f"Increase emboss to at least {profile.min_emboss}mm",
        ))
    return issues


def check_deboss_depth(
    depth: float, node_id: str, profile: ManufacturingProfile,
) -> List[ManufacturingIssue]:
    """Check deboss depth is within printable range."""
    issues = []
    if depth < profile.min_deboss:
        issues.append(ManufacturingIssue(
            code=IssueCode.MIN_DEBOSS, severity=Severity.WARNING,
            message=f"Deboss depth {depth:.2f}mm below minimum {profile.min_deboss}mm",
            node_id=node_id, value=depth, threshold=profile.min_deboss,
            suggestion=f"Increase deboss to at least {profile.min_deboss}mm",
        ))
    return issues


def check_qr_size(
    size: float, node_id: str, profile: ManufacturingProfile,
) -> List[ManufacturingIssue]:
    """Check QR code meets minimum size."""
    issues = []
    if size < profile.min_qr_size:
        issues.append(ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL, severity=Severity.ERROR,
            message=f"QR size {size:.0f}mm below minimum {profile.min_qr_size}mm",
            node_id=node_id, value=size, threshold=profile.min_qr_size,
            suggestion=f"Increase QR to at least {profile.min_qr_size}mm",
        ))
    return issues


def check_qr_module_size(
    qr_size: float, node_id: str, profile: ManufacturingProfile,
    modules: int = 33,
) -> List[ManufacturingIssue]:
    """Check each QR module is printable."""
    module_size = qr_size / modules
    issues = []
    if module_size < profile.min_qr_module:
        issues.append(ManufacturingIssue(
            code=IssueCode.QR_TOO_SMALL, severity=Severity.WARNING,
            message=f"QR module {module_size:.2f}mm below minimum {profile.min_qr_module}mm",
            node_id=node_id, value=module_size, threshold=profile.min_qr_module,
            suggestion=f"Increase QR to at least {profile.min_qr_module * modules:.0f}mm",
        ))
    return issues


def check_text_size(
    font_size: float, node_id: str, profile: ManufacturingProfile,
) -> List[ManufacturingIssue]:
    """Check text is readable after printing."""
    issues = []
    if font_size < profile.min_text_size:
        issues.append(ManufacturingIssue(
            code=IssueCode.TEXT_TOO_SMALL, severity=Severity.WARNING,
            message=f"Text size {font_size:.1f}mm below minimum {profile.min_text_size}mm",
            node_id=node_id, value=font_size, threshold=profile.min_text_size,
            suggestion=f"Increase font to at least {profile.min_text_size}mm",
        ))
    return issues


def check_unsupported_relief(
    mode: str, node_id: str, profile: ManufacturingProfile,
) -> List[ManufacturingIssue]:
    """Check if the relief mode is supported by the process."""
    issues = []
    if mode not in profile.supported_relief_modes:
        issues.append(ManufacturingIssue(
            code=IssueCode.UNSUPPORTED_RELIEF, severity=Severity.WARNING,
            message=f"Relief mode '{mode}' not supported by {profile.process}",
            node_id=node_id,
            suggestion=f"Use one of: {', '.join(profile.supported_relief_modes)}",
        ))
    return issues


def check_gap(
    gap: float, node_id: str, profile: ManufacturingProfile,
) -> List[ManufacturingIssue]:
    """Check minimum gap between features."""
    issues = []
    if gap < profile.min_gap:
        issues.append(ManufacturingIssue(
            code=IssueCode.MIN_GAP, severity=Severity.WARNING,
            message=f"Gap {gap:.2f}mm below minimum {profile.min_gap}mm",
            node_id=node_id, value=gap, threshold=profile.min_gap,
            suggestion=f"Increase gap to at least {profile.min_gap}mm",
        ))
    return issues
