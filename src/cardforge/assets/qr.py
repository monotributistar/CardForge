"""QR code generator — produces valid SVG QR codes via the qrcode library."""

from pathlib import Path

import qrcode
from qrcode.image.svg import SvgPathImage


VALID_ERROR_CORRECTION = {"L", "M", "Q", "H"}

ERROR_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


class QRGenerationError(Exception):
    """Raised when QR generation fails."""
    pass


def generate_qr_svg(
    value: str,
    output_path: Path,
    size_mm: float = 24,
    quiet_zone_mm: float = 2,
    error_correction: str = "M",
) -> Path:
    """Generate a QR code as an SVG file.

    Args:
        value: The data to encode (URL, text, vCard, etc.).
        output_path: Where to write the SVG file.
        size_mm: QR code size in mm (excluding quiet zone).
        quiet_zone_mm: White border around QR in mm.
        error_correction: L, M, Q, or H.

    Returns:
        The output path.

    Raises:
        QRGenerationError: If parameters are invalid or generation fails.
        ValueError: For invalid parameters.
    """
    if not value or not value.strip():
        raise ValueError("QR value must not be empty")
    if size_mm <= 0:
        raise ValueError(f"size_mm must be > 0, got {size_mm}")
    if quiet_zone_mm < 0:
        raise ValueError(f"quiet_zone_mm must be >= 0, got {quiet_zone_mm}")
    if error_correction not in VALID_ERROR_CORRECTION:
        raise ValueError(
            f"error_correction must be one of {VALID_ERROR_CORRECTION}, got '{error_correction}'"
        )

    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_MAP[error_correction],
            box_size=10,  # arbitrary, we control size via SVG attributes
            border=0,  # quiet zone handled separately
        )
        qr.add_data(value)
        qr.make(fit=True)

        # Calculate module size in mm
        modules = qr.modules_count
        total_mm = size_mm + 2 * quiet_zone_mm
        module_mm = size_mm / modules

        # Build SVG manually for precise control
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{total_mm}mm" height="{total_mm}mm" '
            f'viewBox="0 0 {total_mm} {total_mm}">',
            f'<rect x="0" y="0" width="{total_mm}" height="{total_mm}" fill="white"/>',
            f'<g transform="translate({quiet_zone_mm},{quiet_zone_mm})">',
        ]

        for row in range(modules):
            for col in range(modules):
                if qr.modules[row][col]:
                    svg_lines.append(
                        f'<rect x="{col * module_mm}" y="{row * module_mm}" '
                        f'width="{module_mm}" height="{module_mm}" fill="black"/>'
                    )

        svg_lines.append("</g>")
        svg_lines.append("</svg>")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(svg_lines))
        return output_path

    except Exception as e:
        raise QRGenerationError(f"Failed to generate QR code: {e}") from e
