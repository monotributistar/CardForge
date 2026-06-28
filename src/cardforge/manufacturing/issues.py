"""Manufacturing issue types and severity levels."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    """Severity of a manufacturing issue."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class IssueCode(str, Enum):
    """Standard issue codes for manufacturing analysis."""
    # Geometry
    MIN_LINE_WIDTH = "min_line_width"
    MIN_WALL_THICKNESS = "min_wall_thickness"
    MIN_GAP = "min_gap"
    OUTSIDE_BOUNDS = "outside_bounds"

    # Relief
    MIN_EMBOSS = "min_emboss"
    MIN_DEBOSS = "min_deboss"
    UNSUPPORTED_RELIEF = "unsupported_relief"

    # Features
    QR_TOO_SMALL = "qr_too_small"
    QR_QUIET_ZONE = "qr_quiet_zone"
    TEXT_TOO_SMALL = "text_too_small"
    MATERIAL_OVERLAP = "material_overlap"

    # Process
    UNSUPPORTED_FEATURE = "unsupported_feature"


@dataclass
class ManufacturingIssue:
    """A single issue found during manufacturing analysis."""

    code: IssueCode
    severity: Severity
    message: str
    node_id: Optional[str] = None
    suggestion: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "node_id": self.node_id,
            "suggestion": self.suggestion,
            "value": self.value,
            "threshold": self.threshold,
        }
