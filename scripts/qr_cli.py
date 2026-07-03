#!/usr/bin/env python3
"""QR CLI tool: generates QR SVG via Python qrcode library.

Usage:
    uv run python scripts/qr_cli.py "https://example.com" 24 2
    → prints SVG string
"""

import sys
import io

def generate_qr_svg(text, size_mm=24, quiet_zone_mm=2):
    import qrcode
    from qrcode.image.svg import SvgPathImage
    
    qr = qrcode.QRCode(
        version=None,  # auto
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=0,
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    modules = len(qr.modules)
    total_px = int(size_mm * 4)
    data_area_mm = size_mm - 2 * quiet_zone_mm
    module_px = (data_area_mm * 4) / modules
    offset_px = quiet_zone_mm * 4
    
    rects = []
    rects.append(f'<rect x="0" y="0" width="{total_px}" height="{total_px}" fill="white"/>')
    for r in range(modules):
        for c in range(modules):
            if qr.modules[r][c]:
                x = offset_px + c * module_px
                y = offset_px + r * module_px
                rects.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{module_px:.1f}" '
                    f'height="{module_px:.1f}" fill="black"/>'
                )
    return '\n'.join(rects)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/qr_cli.py <text> [size_mm] [quiet_zone_mm]", file=sys.stderr)
        sys.exit(1)
    
    text = sys.argv[1]
    size_mm = float(sys.argv[2]) if len(sys.argv) > 2 else 24
    quiet = float(sys.argv[3]) if len(sys.argv) > 3 else 2
    
    try:
        svg = generate_qr_svg(text, size_mm, quiet)
        print(svg)
    except Exception as e:
        print(f"<text>QR Error: {e}</text>")
        sys.exit(1)
