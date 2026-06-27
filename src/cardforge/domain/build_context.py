"""BuildContext — manufacturing settings and resolved configuration."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cardforge.domain.constraints import ConstraintIssue, ConstraintResult
from cardforge.domain.material import Material, DEFAULT_MATERIALS


@dataclass
class ManufacturingSettings:
    """Manufacturing parameters for the print process."""

    process: str = "fdm"
    nozzle: float = 0.4
    layer_height: float = 0.2
    units: str = "mm"


@dataclass
class BuildContext:
    """Holds all context needed during a build.

    Includes manufacturing settings, materials, resolved config,
    and accumulates warnings and errors during validation.
    """

    manufacturing: ManufacturingSettings = field(default_factory=ManufacturingSettings)
    materials: Dict[str, Material] = field(default_factory=lambda: dict(DEFAULT_MATERIALS))
    resolved_config: Dict[str, Any] = field(default_factory=dict)
    constraint_result: ConstraintResult = field(default_factory=ConstraintResult)

    @property
    def errors(self) -> List[ConstraintIssue]:
        return self.constraint_result.errors

    @property
    def warnings(self) -> List[ConstraintIssue]:
        return self.constraint_result.warnings

    @property
    def has_errors(self) -> bool:
        return self.constraint_result.has_errors

    def add_error(self, message: str, feature_id: Optional[str] = None) -> None:
        from cardforge.domain.geometry import Severity
        self.constraint_result.add(ConstraintIssue(
            severity=Severity.ERROR, message=message, feature_id=feature_id
        ))

    def add_warning(self, message: str, feature_id: Optional[str] = None) -> None:
        from cardforge.domain.geometry import Severity
        self.constraint_result.add(ConstraintIssue(
            severity=Severity.WARNING, message=message, feature_id=feature_id
        ))

    def get_material(self, material_id: str) -> Optional[Material]:
        """Get a material by id, or None if not found."""
        return self.materials.get(material_id)
