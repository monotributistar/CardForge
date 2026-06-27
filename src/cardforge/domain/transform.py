"""Transform — position, rotation, and scale for domain objects."""

from dataclasses import dataclass, field

from cardforge.domain.geometry import Position


@dataclass
class Transform:
    """2D transform with position, rotation, and scale.

    Rotation is expressed in degrees clockwise around the position origin.
    """

    position: Position = field(default_factory=Position)
    rotation: float = 0.0  # degrees, clockwise
    scale_x: float = 1.0
    scale_y: float = 1.0

    def to_dict(self) -> dict:
        return {
            "position": {"x": self.position.x, "y": self.position.y},
            "rotation": self.rotation,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
        }
