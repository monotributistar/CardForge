"""Kernel value types — bounds, trace records, compiled scene.

`CompiledScene` + `CompileTrace` are the contract between the kernel and
everything downstream (3MF/STL export, constraints, manufacturing analysis,
API stats). Nothing downstream touches CrossSections or feature params.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from manifold3d import Manifold


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Bounds:
    """Axis-aligned rectangle in document space (mm, top-left origin, y-down)."""

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def area(self) -> float:
        return self.width * self.height

    def contains(self, other: "Bounds") -> bool:
        return (self.x <= other.x and self.y <= other.y
                and other.right <= self.right and other.bottom <= self.bottom)

    def intersects(self, other: "Bounds") -> bool:
        return not (other.x >= self.right or other.right <= self.x
                    or other.y >= self.bottom or other.bottom <= self.y)

    def expand(self, margin: float) -> "Bounds":
        return Bounds(self.x - margin, self.y - margin,
                      self.width + 2 * margin, self.height + 2 * margin)


@dataclass
class ConstraintIssue:
    severity: Severity
    code: str
    message: str
    feature_id: Optional[str] = None
    face_id: Optional[str] = None


@dataclass
class FeatureRecord:
    """Per-feature facts recorded during compilation.

    Feeds constraints and manufacturing analysis without exposing geometry.
    """

    feature_id: str
    face_id: str
    type: str
    material: str
    relief_mode: str
    relief_value: float  # height for emboss, depth otherwise, 0 for cut
    bounds: Bounds       # document space
    area: float = 0.0    # 2D shape area (mm²)
    extra: Dict[str, Any] = field(default_factory=dict)  # qr_module_mm, font_size, ...


@dataclass
class CompileTrace:
    records: List[FeatureRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)  # feature ids skipped (+reason in warnings)
    elapsed_ms: float = 0.0

    def by_face(self, face_id: str) -> List[FeatureRecord]:
        return [r for r in self.records if r.face_id == face_id]


@dataclass
class CompiledScene:
    """The kernel's output: a disjoint partition of the object volume."""

    volumes: Dict[str, Manifold]  # material id → solid (may be empty Manifold)
    thickness: float
    outline_bounds: Bounds        # document space bounds of the outline
    material_order: List[str]     # palette order, for deterministic export

    def non_empty(self) -> Dict[str, Manifold]:
        return {k: v for k, v in self.volumes.items()
                if not v.is_empty() and v.volume() > 1e-9}
