"""Material grouping — groups features by material for multi-color STL export."""

from typing import Dict, List

from cardforge.domain.card import Card
from cardforge.domain.feature import Feature


def group_features_by_material(card: Card) -> Dict[str, List[Feature]]:
    """Group all visible features by material ID.

    The 'base' material group is always present (for the card body).
    Features are sorted by z_index within each group.

    Args:
        card: Populated Card domain object.

    Returns:
        Dict mapping material_id to sorted list of features.
        The 'base' key always exists.
    """
    groups: Dict[str, List[Feature]] = {}

    # Ensure base group always exists
    groups["base"] = []

    for face in card.faces.values():
        for feature in face.sorted_features():
            if not feature.visible:
                continue
            mat_id = feature.material.id if feature.material else "base"
            if mat_id not in groups:
                groups[mat_id] = []
            groups[mat_id].append(feature)

    return groups


def get_material_filename(material_id: str, color_name: str = "", index: int = 1) -> str:
    """Generate a deterministic filename for a material STL.

    Format: {index:02d}_{material_id}_{safe_name}.stl

    Args:
        material_id: The material identifier (base, text, accent, etc.).
        color_name: Optional color name for the filename.
        index: Sort index (1-based).

    Returns:
        Sanitized filename.
    """
    import re
    safe_color = re.sub(r"[^a-z0-9_]", "", (color_name or material_id).lower())
    if not safe_color:
        safe_color = material_id
    return f"{index:02d}_{material_id}_{safe_color}.stl"
