"""Manufacturing report — result of analyzing geometry against a profile."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cardforge.manufacturing.issues import ManufacturingIssue, Severity
from cardforge.manufacturing.metrics import ManufacturingMetrics
from cardforge.manufacturing.profiles import ManufacturingProfile


@dataclass
class ManufacturingFix:
    """A suggested fix for a manufacturing issue."""

    node_id: Optional[str] = None
    description: str = ""
    action: str = ""  # increase_size, move_position, change_material, etc.
    suggested_value: Optional[float] = None


@dataclass
class ManufacturingReport:
    """Complete manufacturing analysis report."""

    profile: ManufacturingProfile = field(default_factory=ManufacturingProfile)
    issues: List[ManufacturingIssue] = field(default_factory=list)
    metrics: ManufacturingMetrics = field(default_factory=ManufacturingMetrics)
    fixes: List[ManufacturingFix] = field(default_factory=list)

    @property
    def errors(self) -> List[ManufacturingIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def fatals(self) -> List[ManufacturingIssue]:
        return [i for i in self.issues if i.severity == Severity.FATAL]

    @property
    def warnings(self) -> List[ManufacturingIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def infos(self) -> List[ManufacturingIssue]:
        return [i for i in self.issues if i.severity == Severity.INFO]

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0 or len(self.fatals) > 0

    @property
    def is_manufacturable(self) -> bool:
        return not self.has_errors

    @property
    def score(self) -> int:
        """Compute a manufacturability score from 0 (not manufacturable) to 100 (perfect).

        Scoring:
            - Start at 100
            - FATAL: -40 each
            - ERROR: -15 each
            - WARNING: -5 each
            - INFO: -1 each
            Minimum score: 0
        """
        s = 100
        s -= len(self.fatals) * 40
        s -= len(self.errors) * 15
        s -= len(self.warnings) * 5
        s -= len(self.infos) * 1
        return max(0, min(100, s))

    @property
    def score_label(self) -> str:
        s = self.score
        if s >= 95:
            return "Excellent — ready to print"
        elif s >= 80:
            return "Good — printable with minor warnings"
        elif s >= 60:
            return "Fair — review warnings before printing"
        elif s >= 30:
            return "Poor — significant issues"
        else:
            return "Not manufacturable — fix errors first"

    @property
    def suggestions(self) -> List[str]:
        """Collect all suggestions from issues."""
        return [i.suggestion for i in self.issues if i.suggestion]

    def add_issue(self, issue: ManufacturingIssue) -> None:
        self.issues.append(issue)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile.to_dict(),
            "score": self.score,
            "score_label": self.score_label,
            "is_manufacturable": self.is_manufacturable,
            "error_count": len(self.errors),
            "fatal_count": len(self.fatals),
            "warning_count": len(self.warnings),
            "info_count": len(self.infos),
            "issues": [i.to_dict() for i in self.issues],
            "metrics": self.metrics.to_dict(),
            "suggestions": self.suggestions,
        }
