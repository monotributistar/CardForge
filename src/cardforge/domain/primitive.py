"""Primitive — base geometric shapes. Features produce one or more Primitives.

Primitives are the bridge between semantic Features and OpenSCAD generation.
In this phase they are modeled but do not generate actual geometry yet.
"""

from dataclasses import dataclass, field
from typing import Optional

from cardforge.domain.geometry import Bounds, Position, Size
from cardforge.domain.material import Material
from cardforge.domain.relief import Relief
from cardforge.domain.transform import Transform


@dataclass
class Primitive:
    """Base geometric primitive.

    Features will produce one or more Primitives in a future phase.
    Each primitive maps to an OpenSCAD module call.
    """

    id: str
    type: str
    transform: Transform = field(default_factory=Transform)
    material: Optional[Material] = None
    relief: Relief = field(default_factory=Relief.flush)
    bounds: Bounds = field(default_factory=Bounds)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "transform": self.transform.to_dict(),
            "material": self.material.id if self.material else None,
            "relief": self.relief.to_dict(),
            "bounds": self.bounds.to_dict(),
        }


@dataclass
class RectanglePrimitive(Primitive):
    """Axis-aligned rectangle primitive."""

    type: str = "rectangle"

    @classmethod
    def create(
        cls,
        id: str,
        bounds: Bounds,
        material: Optional[Material] = None,
        relief: Optional[Relief] = None,
    ) -> "RectanglePrimitive":
        return cls(
            id=id,
            bounds=bounds,
            material=material,
            relief=relief or Relief.flush(),
        )


@dataclass
class TextPrimitive(Primitive):
    """Text primitive with font and lines."""

    type: str = "text"
    lines: list[str] = field(default_factory=list)
    font: str = "Montserrat"
    font_size: float = 3.0
    font_style: str = "bold"
    align: str = "left"
    line_height: float = 1.4


@dataclass
class SVGPrimitive(Primitive):
    """SVG-based primitive (QR, logo, pattern)."""

    type: str = "svg"
    svg_path: str = ""
    svg_content: Optional[str] = None


@dataclass
class GroupPrimitive(Primitive):
    """Group of primitives rendered together."""

    type: str = "group"
    children: list[Primitive] = field(default_factory=list)
