"""Manufacturing metrics — computed measurements about the geometry."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ManufacturingMetrics:
    """Computed metrics from geometry analysis."""

    feature_count: int = 0
    svg_count: int = 0
    text_count: int = 0
    extrude_count: int = 0

    smallest_line: float = 999.0
    largest_line: float = 0.0
    smallest_emboss: float = 999.0
    largest_emboss: float = 0.0
    smallest_deboss: float = 999.0
    largest_deboss: float = 0.0
    smallest_text: float = 999.0
    smallest_qr: float = 999.0
    min_wall: float = 999.0

    estimated_materials: List[str] = field(default_factory=list)
    estimated_colors: int = 0

    def update_line(self, width: float) -> None:
        self.smallest_line = min(self.smallest_line, width)
        self.largest_line = max(self.largest_line, width)

    def update_emboss(self, height: float) -> None:
        if height > 0:
            self.smallest_emboss = min(self.smallest_emboss, height)
            self.largest_emboss = max(self.largest_emboss, height)

    def update_deboss(self, depth: float) -> None:
        if depth > 0:
            self.smallest_deboss = min(self.smallest_deboss, depth)
            self.largest_deboss = max(self.largest_deboss, depth)

    def update_text(self, size: float) -> None:
        self.smallest_text = min(self.smallest_text, size)

    def update_qr(self, size: float) -> None:
        self.smallest_qr = min(self.smallest_qr, size)

    def update_wall(self, thickness: float) -> None:
        self.min_wall = min(self.min_wall, thickness)

    def to_dict(self) -> dict:
        return {
            "feature_count": self.feature_count,
            "svg_count": self.svg_count,
            "text_count": self.text_count,
            "extrude_count": self.extrude_count,
            "smallest_line_mm": self.smallest_line if self.smallest_line < 999 else 0,
            "largest_line_mm": self.largest_line,
            "smallest_emboss_mm": self.smallest_emboss if self.smallest_emboss < 999 else 0,
            "largest_emboss_mm": self.largest_emboss,
            "smallest_deboss_mm": self.smallest_deboss if self.smallest_deboss < 999 else 0,
            "largest_deboss_mm": self.largest_deboss,
            "smallest_text_mm": self.smallest_text if self.smallest_text < 999 else 0,
            "smallest_qr_mm": self.smallest_qr if self.smallest_qr < 999 else 0,
            "min_wall_mm": self.min_wall if self.min_wall < 999 else 0,
            "estimated_materials": self.estimated_materials,
            "estimated_colors": self.estimated_colors,
        }
