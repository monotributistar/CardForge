"""Core domain types: Position, Size, Bounds, enums, and unit conventions.

CardForge works exclusively in millimeters internally.
All coordinates use a 2D cartesian system with origin at top-left.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ── Units ────────────────────────────────────────────────────────────────────

# CardForge internal unit = millimeter. All dimensions, positions,
# sizes, relief heights, and bounds are expressed in mm.

UNIT = "mm"


# ── Enums ─────────────────────────────────────────────────────────────────────

class Anchor(str, Enum):
    """Anchor point for positioning. Origin at top-left of face."""

    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    CENTER_LEFT = "center-left"
    CENTER = "center"
    CENTER_RIGHT = "center-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"


class ReliefMode(str, Enum):
    """How a feature interacts with the base surface in Z dimension."""

    EMBOSS = "emboss"  # Raised (+Z)
    DEBOSS = "deboss"  # Recessed (−Z)
    FLUSH = "flush"    # Coplanar (±0)
    CUT = "cut"        # Through-cut (subtractive)


class MaterialRole(str, Enum):
    """Intended manufacturing role of a material."""

    BASE = "base"
    TEXT = "text"
    ACCENT = "accent"
    SUPPORT = "support"
    TRANSPARENT = "transparent"


class FeatureType(str, Enum):
    """Known feature type identifiers."""

    TEXT_BLOCK = "text-block"
    QR_CODE = "qr"
    PATTERN = "pattern"
    LOGO = "logo"
    FRAME = "frame"
    CORNER = "corner"
    CONTACT_BLOCK = "contact-block"
    HUEFORGE = "hueforge"


class LayerRole(str, Enum):
    """Semantic role of a layer within a face."""

    BASE = "base"
    BACKGROUND = "background"
    DECORATIVE = "decorative"
    CONTENT = "content"
    FUNCTIONAL = "functional"
    ACCENT = "accent"
    DEBUG = "debug"


class Severity(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"


class ManufacturingProcess(str, Enum):
    """Supported manufacturing processes."""

    FDM = "fdm"
    SLA = "sla"  # future
    SLS = "sls"  # future


# ── Geometry ──────────────────────────────────────────────────────────────────

@dataclass
class Position:
    """2D position in mm, relative to a face's top-left origin."""

    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Position") -> "Position":
        return Position(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Position") -> "Position":
        return Position(self.x - other.x, self.y - other.y)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Size:
    """2D size in mm."""

    width: float = 0.0
    height: float = 0.0

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_tuple(self) -> tuple[float, float]:
        return (self.width, self.height)

    def __bool__(self) -> bool:
        return self.width > 0 and self.height > 0


@dataclass
class Bounds:
    """Axis-aligned bounding box in mm, top-left origin."""

    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Position:
        return Position(self.x + self.width / 2, self.y + self.height / 2)

    @property
    def top_left(self) -> Position:
        return Position(self.x, self.y)

    @property
    def area(self) -> float:
        return self.width * self.height

    def contains(self, other: "Bounds") -> bool:
        """Check if this bounds fully contains another."""
        return (
            self.x <= other.x
            and self.y <= other.y
            and self.right >= other.right
            and self.bottom >= other.bottom
        )

    def intersects(self, other: "Bounds") -> bool:
        """Check if this bounds overlaps with another."""
        return not (
            self.right <= other.x
            or other.right <= self.x
            or self.bottom <= other.y
            or other.bottom <= self.y
        )

    def expand(self, margin: float) -> "Bounds":
        """Return a new Bounds expanded by margin on all sides."""
        return Bounds(
            x=self.x - margin,
            y=self.y - margin,
            width=self.width + 2 * margin,
            height=self.height + 2 * margin,
        )

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}
