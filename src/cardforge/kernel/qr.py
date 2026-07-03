"""QR code → CrossSection, straight from the module matrix (no SVG roundtrip)."""

from __future__ import annotations

from dataclasses import dataclass

from manifold3d import CrossSection, FillRule

from cardforge.assets.qr import generate_qr_matrix
from cardforge.assets.vcard import build_vcard


@dataclass
class QRResult:
    cross_section: CrossSection  # feature-local (anchor top-left, y-up)
    modules: int                 # matrix dimension (e.g. 29 for a 29×29 code)
    module_mm: float             # printed size of one module
    total_mm: float              # size including quiet zone


def format_qr_payload(qr_type: str, fields: dict) -> str:
    """v2 qr feature (qrType + fields) → encoded payload string."""
    if qr_type == "url":
        return fields.get("url", "")
    if qr_type == "text":
        return fields.get("text", "")
    if qr_type == "wifi":
        ssid = fields.get("wifi_ssid", "")
        pwd = fields.get("wifi_password", "")
        enc = fields.get("wifi_encryption", "WPA")
        return f"WIFI:T:{enc};S:{ssid};P:{pwd};;"
    if qr_type == "email":
        addr = fields.get("email_address", "")
        subject = fields.get("email_subject", "")
        body = fields.get("email_body", "")
        params = []
        if subject:
            params.append(f"subject={subject}")
        if body:
            params.append(f"body={body}")
        return f"mailto:{addr}" + (("?" + "&".join(params)) if params else "")
    if qr_type == "vcard":
        return build_vcard({
            "name": fields.get("vcard_name", ""),
            "title": fields.get("vcard_title", ""),
            "phone": fields.get("vcard_phone", ""),
            "email": fields.get("vcard_email", ""),
            "website": fields.get("vcard_website", ""),
        })
    raise ValueError(f"unknown qr type: {qr_type}")


def qr_cross_section(payload: str, size_mm: float, quiet_zone_mm: float = 2.0,
                     error_correction: str = "M") -> QRResult:
    """QR modules as one CrossSection.

    The dark modules occupy size_mm×size_mm; the quiet zone offsets them
    inside a (size+2·qz)² box whose top-left is the anchor. The quiet zone
    itself produces no geometry (in 3D it is simply flat base surface).
    """
    matrix = generate_qr_matrix(payload, error_correction)
    n = len(matrix)
    mm = size_mm / n
    total = size_mm + 2 * quiet_zone_mm

    squares = []
    for r, row in enumerate(matrix):
        for c, filled in enumerate(row):
            if not filled:
                continue
            x = quiet_zone_mm + c * mm
            y_top = -(quiet_zone_mm + r * mm)  # y-up local space
            squares.append([
                (x, y_top - mm), (x + mm, y_top - mm),
                (x + mm, y_top), (x, y_top),
            ])
    cs = (CrossSection(squares, fillrule=FillRule.Positive).simplify()
          if squares else CrossSection())
    return QRResult(cs, n, mm, total)
