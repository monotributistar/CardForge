"""Layer — a z-ordered group of features within a face."""

from dataclasses import dataclass, field
from typing import List, Optional

from cardforge.domain.feature import Feature
from cardforge.domain.geometry import Bounds
from cardforge.domain.material import Material


@dataclass
class Layer:
    """A z-ordered group of features within a face.

    Layers provide semantic grouping: base, background, decorative,
    content, functional, accent.
    """

    id: str
    name: str = ""
    role: str = "content"
    z_index: int = 0
    visible: bool = True
    features: List[Feature] = field(default_factory=list)

    def all_features(self) -> List[Feature]:
        """Return all features in this layer."""
        return list(self.features)

    def features_by_material(self, material: Material) -> List[Feature]:
        """Return features using the given material."""
        return [f for f in self.features if f.material == material]

    def sorted_features(self) -> List[Feature]:
        """Return features sorted by z_index ascending."""
        return sorted(self.features, key=lambda f: f.z_index)

    def bounds(self) -> Bounds:
        """Return union bounds of all visible features, or empty bounds."""
        if not self.features:
            return Bounds()
        visible = [f for f in self.features if f.visible]
        if not visible:
            return Bounds()
        # Compute union of all feature bounds
        min_x = min(f.position.x for f in visible)
        min_y = min(f.position.y for f in visible)
        max_x = max(f.position.x + f.size.width for f in visible)
        max_y = max(f.position.y + f.size.height for f in visible)
        return Bounds(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "z_index": self.z_index,
            "visible": self.visible,
            "features": [f.to_dict() for f in self.features],
        }
