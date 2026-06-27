"""Theme — color and material configuration for preview rendering."""

from dataclasses import dataclass
from typing import Dict, Optional

from cardforge.domain.material import Material


@dataclass
class Theme:
    """Visual theme for SVG preview rendering."""

    background_color: str = "#ffffff"
    card_base_color: str = "#1a1a1a"
    text_color: str = "#ffffff"
    accent_color: str = "#ffd700"
    stroke_color: str = "#333333"
    stroke_width: float = 0.5
    corner_radius: float = 4.0
    font_family: str = "sans-serif"

    @classmethod
    def from_materials(cls, materials: Dict[str, Material]) -> "Theme":
        """Create a theme from material definitions."""
        theme = cls()
        if "base" in materials:
            theme.card_base_color = materials["base"].color
        if "text" in materials:
            theme.text_color = materials["text"].color
        if "accent" in materials:
            theme.accent_color = materials["accent"].color
        return theme

    def get_color(self, material: Optional[Material]) -> str:
        """Get the hex color for a material, falling back to defaults."""
        if material is None:
            return self.text_color
        # Standard materials use theme colors; custom materials use their own color
        if material.id in ("base", "text", "accent"):
            color_map = {
                "base": self.card_base_color,
                "text": self.text_color,
                "accent": self.accent_color,
            }
            return color_map.get(material.id, material.color)
        return material.color
