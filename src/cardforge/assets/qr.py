"""QR code generation — module matrix via the qrcode library.

The geometry kernel (kernel/qr.py) turns the matrix directly into a
CrossSection; there is no SVG intermediate.
"""

import qrcode

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
