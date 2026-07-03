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


def generate_qr_matrix(value: str, error_correction: str = "M") -> list:
    """Generate the raw QR module matrix (list of rows of bools).

    Kernel-facing API: the geometry kernel turns this matrix directly into
    a CrossSection, no SVG file roundtrip.

    Raises:
        ValueError: empty value or invalid error correction level.
        QRGenerationError: if the qrcode library fails.
    """
    if not value or not value.strip():
        raise ValueError("QR value must not be empty")
    if error_correction not in VALID_ERROR_CORRECTION:
        raise ValueError(
            f"error_correction must be one of {VALID_ERROR_CORRECTION}, got '{error_correction}'")
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_MAP[error_correction],
            box_size=1,
            border=0,
        )
        qr.add_data(value)
        qr.make(fit=True)
        return [list(row) for row in qr.modules]
    except Exception as e:
        raise QRGenerationError(f"Failed to generate QR matrix: {e}") from e


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

        # Build SVG manually for precise control.
        #
        # Module rects are emitted flat, at absolute coordinates (the quiet-zone
        # offset is folded into each x/y) and WITHOUT a white background rect.
        # This is deliberate so the file imports correctly into OpenSCAD:
        #   - OpenSCAD's SVG import drops rects nested inside <g transform=...>,
        #     so a grouped QR would import as an empty (or background-only) shape.
        #   - OpenSCAD ignores fill colour, so a white background rect would be
        #     imported as a solid block, burying the modules.
        # The 2D card preview renders its own QR (see Studio QRGenerator), so the
        # visual quiet zone is not needed here — in 3D it is just flat card.
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{total_mm}mm" height="{total_mm}mm" '
            f'viewBox="0 0 {total_mm} {total_mm}">',
        ]

        for row in range(modules):
            for col in range(modules):
                if qr.modules[row][col]:
                    x = quiet_zone_mm + col * module_mm
                    y = quiet_zone_mm + row * module_mm
                    svg_lines.append(
                        f'<rect x="{x}" y="{y}" '
                        f'width="{module_mm}" height="{module_mm}" fill="black"/>'
                    )

        svg_lines.append("</svg>")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(svg_lines))
        return output_path

    except Exception as e:
        raise QRGenerationError(f"Failed to generate QR code: {e}") from e
