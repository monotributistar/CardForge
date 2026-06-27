"""Pattern generator — produces SVG patterns for text-repeat, dots, and grid."""

import math
from pathlib import Path

from cardforge.assets.svg_utils import svg_header, svg_footer, svg_rect, svg_text, svg_group


class PatternGenerationError(Exception):
    """Raised when pattern generation fails."""
    pass


def generate_text_repeat_pattern_svg(
    text: str,
    output_path: Path,
    width_mm: float,
    height_mm: float,
    spacing_mm: float = 10.0,
    rotation_deg: float = -25,
    font_size_mm: float = 4.0,
    opacity: float = 1.0,
    color: str = None,
) -> Path:
    """Generate a repeating text pattern as SVG.

    Args:
        text: Text to repeat across the pattern.
        output_path: Where to save the SVG.
        width_mm: Pattern width (usually face width).
        height_mm: Pattern height (usually face height).
        spacing_mm: Center-to-center spacing between text repetitions.
        rotation_deg: Rotation angle in degrees.
        font_size_mm: Font size in mm.
        opacity: Opacity (0.0 to 1.0).
        color: Text color (hex or name). Defaults to semi-transparent.

    Returns:
        The output path.

    Raises:
        PatternGenerationError: On invalid parameters.
        ValueError: On bad input values.
    """
    if not text or not text.strip():
        raise ValueError("text must not be empty")
    if width_mm <= 0 or height_mm <= 0:
        raise ValueError("width_mm and height_mm must be > 0")
    if spacing_mm <= 0:
        raise ValueError(f"spacing_mm must be > 0, got {spacing_mm}")

    fill_color = color or "#ffffff"
    opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

    lines = []
    lines.append(svg_header(width_mm, height_mm))

    # Background
    lines.append(svg_rect(0, 0, width_mm, height_mm, fill="none"))

    # Calculate grid positions
    cols = max(1, math.ceil(width_mm / spacing_mm) + 1)
    rows = max(1, math.ceil(height_mm / spacing_mm) + 1)

    # Center the grid
    offset_x = (width_mm - (cols - 1) * spacing_mm) / 2
    offset_y = (height_mm - (rows - 1) * spacing_mm) / 2

    for row in range(rows):
        for col in range(cols):
            x = offset_x + col * spacing_mm
            y = offset_y + row * spacing_mm
            transform = f"rotate({rotation_deg},{x},{y})"
            text_elem = (
                f'<text x="{x}" y="{y}" font-family="sans-serif" '
                f'font-size="{font_size_mm}" fill="{fill_color}"{opacity_attr} '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'transform="{transform}">{text}</text>'
            )
            lines.append(text_elem)

    lines.append(svg_footer())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    return output_path
