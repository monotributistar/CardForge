"""Material model — represents manufacturing intent, not just color."""

from dataclasses import dataclass, field
from typing import Optional

from cardforge.domain.geometry import ReliefMode


@dataclass
class Material:
    """A material represents a physical filament with a role in the object.

    Materials drive multi-color STL export: each unique material
    produces its own STL file for multi-material printing.
    """

    id: str
    name: str
    color: str = "#000000"  # hex color for previews
    role: str = "base"       # base, text, accent, support, transparent

    def __post_init__(self):
        if not self.id:
            raise ValueError("Material id must not be empty")
        if not self.name:
            raise ValueError("Material name must not be empty")
        if not self.color.startswith("#"):
            raise ValueError(f"Material color must be hex (e.g., #FF0000), got: {self.color}")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Material):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "role": self.role,
        }


# ── Default materials ─────────────────────────────────────────────────────────

DEFAULT_MATERIALS = {
    "base": Material(id="base", name="Black PLA", color="#1a1a1a", role="base"),
    "text": Material(id="text", name="White PLA", color="#ffffff", role="text"),
    "accent": Material(id="accent", name="Gold PLA", color="#ffd700", role="accent"),
}
