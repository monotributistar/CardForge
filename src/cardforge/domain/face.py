"""Face — one side of a flat object (front, back, etc.)."""

from dataclasses import dataclass, field
from typing import List, Optional

from cardforge.domain.feature import Feature
from cardforge.domain.geometry import Bounds
from cardforge.domain.layer import Layer
from cardforge.domain.material import Material


@dataclass
class Face:
    """One side of a flat object, containing layers of features."""

    id: str
    name: str = ""
    width: float = 85.0
    height: float = 54.0
    layers: List[Layer] = field(default_factory=list)

    def all_features(self) -> List[Feature]:
        """Return all features across all layers."""
        result = []
        for layer in self.layers:
            result.extend(layer.all_features())
        return result

    def features_by_layer(self, layer_id: str) -> List[Feature]:
        """Return features in a specific layer."""
        for layer in self.layers:
            if layer.id == layer_id:
                return layer.all_features()
        return []

    def features_by_material(self, material: Material) -> List[Feature]:
        """Return all features using the given material."""
        result = []
        for layer in self.layers:
            result.extend(layer.features_by_material(material))
        return result

    def sorted_features(self) -> List[Feature]:
        """Return all features sorted by layer z_index, then feature z_index."""
        result = []
        for layer in sorted(self.layers, key=lambda l: l.z_index):
            result.extend(layer.sorted_features())
        return result

    def bounds(self) -> Bounds:
        """Return the face bounds (full face area)."""
        return Bounds(x=0, y=0, width=self.width, height=self.height)

    def get_layer(self, layer_id: str) -> Optional[Layer]:
        """Get a layer by id."""
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "layers": [l.to_dict() for l in self.layers],
        }
