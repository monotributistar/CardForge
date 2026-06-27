"""Feature — semantic/functional element on a face's layer.

Features are the user-facing building blocks: text, QR, pattern, logo, etc.
They will produce Primitives in a future phase for SCAD generation.
"""

from dataclasses import dataclass, field
from typing import Optional

from cardforge.domain.geometry import Bounds, Position, Size
from cardforge.domain.material import Material
from cardforge.domain.relief import Relief


@dataclass
class Feature:
    """Base feature — a semantic element on a face layer.

    Every feature has a common interface: id, type, position, size,
    material, relief, visibility, and zIndex.
    """

    id: str
    type: str
    name: str = ""
    face: str = "front"
    layer: str = "content"
    position: Position = field(default_factory=Position)
    size: Size = field(default_factory=Size)
    material: Optional[Material] = None
    relief: Relief = field(default_factory=Relief.flush)
    visible: bool = True
    z_index: int = 0
    metadata: dict = field(default_factory=dict)

    def bounds(self) -> Bounds:
        """Return the axis-aligned bounding box of this feature."""
        return Bounds(
            x=self.position.x,
            y=self.position.y,
            width=self.size.width,
            height=self.size.height,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "face": self.face,
            "layer": self.layer,
            "position": self.position.to_tuple(),
            "size": self.size.to_tuple(),
            "material": self.material.id if self.material else None,
            "relief": self.relief.to_dict(),
            "visible": self.visible,
            "z_index": self.z_index,
        }


# ── Concrete feature types ────────────────────────────────────────────────────


@dataclass
class TextBlockFeature(Feature):
    """Multi-line text feature with font and alignment."""

    type: str = "text-block"
    lines: list[str] = field(default_factory=list)
    font: str = "Montserrat"
    font_size: float = 3.0
    font_style: str = "bold"
    align: str = "left"
    line_height: float = 1.4


@dataclass
class QRCodeFeature(Feature):
    """QR code feature generated from vCard, URL, or text data."""

    type: str = "qr"
    qr_type: str = "vcard"  # vcard, url, text, wifi
    target: str = "owner"
    error_correction: str = "M"  # L, M, Q, H
    quiet_zone: float = 2.0


@dataclass
class PatternFeature(Feature):
    """Repeating decorative pattern feature."""

    type: str = "pattern"
    pattern_type: str = "text-repeat"  # text-repeat, grid, hex, stripes, svg-file
    text: str = ""
    spacing: float = 10.0
    rotation_degrees: float = 0.0
    svg_file: Optional[str] = None


@dataclass
class LogoFeature(Feature):
    """Logo from SVG file."""

    type: str = "logo"
    svg_file: str = ""


@dataclass
class FrameFeature(Feature):
    """Border/frame around the object edge."""

    type: str = "frame"
    frame_style: str = "border"  # border, double, groove, bevel
    frame_width: float = 2.0
    inset: float = 0.0


@dataclass
class CornerDecorationFeature(Feature):
    """Corner treatment applied to all four corners."""

    type: str = "corner"
    corner_style: str = "round"  # round, notch, chamfer, cutout
    radius: float = 4.0
