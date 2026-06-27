"""Card — the primary domain object for a 3D flat object."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cardforge.domain.face import Face
from cardforge.domain.feature import Feature
from cardforge.domain.geometry import Bounds, Size
from cardforge.domain.material import Material
from cardforge.domain.constraints import ConstraintResult


@dataclass
class Card:
    """A 3D-printable flat object with faces, materials, and metadata.

    This is the central domain object. A factory converts a resolved
    config dict into a Card instance.
    """

    id: str
    name: str = ""
    width: float = 85.0
    height: float = 54.0
    thickness: float = 1.8
    corner_radius: float = 4.0
    object_type: str = "business-card"

    materials: Dict[str, Material] = field(default_factory=dict)
    faces: Dict[str, Face] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    # ── Face access ──────────────────────────────────────────────────────

    def get_face(self, face_id: str) -> Optional[Face]:
        """Get a face by id (e.g., 'front', 'back')."""
        return self.faces.get(face_id)

    @property
    def front(self) -> Optional[Face]:
        return self.faces.get("front")

    @property
    def back(self) -> Optional[Face]:
        return self.faces.get("back")

    # ── Feature queries ──────────────────────────────────────────────────

    def all_features(self) -> List[Feature]:
        """Return every feature across all faces and layers."""
        result = []
        for face in self.faces.values():
            result.extend(face.all_features())
        return result

    def features_by_material(self, material_id: str) -> List[Feature]:
        """Return all features using a specific material."""
        material = self.materials.get(material_id)
        if not material:
            return []
        result = []
        for face in self.faces.values():
            result.extend(face.features_by_material(material))
        return result

    def sorted_features(self) -> List[Feature]:
        """Return all features sorted by face, layer z, feature z."""
        result = []
        # Front first, then back
        for face_id in ("front", "back"):
            face = self.faces.get(face_id)
            if face:
                result.extend(face.sorted_features())
        return result

    # ── Bounds ───────────────────────────────────────────────────────────

    def bounds(self) -> Bounds:
        """Return the card's full 2D bounds."""
        return Bounds(x=0, y=0, width=self.width, height=self.height)

    def size(self) -> Size:
        """Return the card's 2D size."""
        return Size(width=self.width, height=self.height)

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "thickness": self.thickness,
            "corner_radius": self.corner_radius,
            "object_type": self.object_type,
            "materials": {k: v.to_dict() for k, v in self.materials.items()},
            "faces": {k: v.to_dict() for k, v in self.faces.items()},
        }
