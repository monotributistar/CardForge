"""SVG Preview Renderer — renders face previews from domain model."""

from pathlib import Path
from typing import Optional

from cardforge.domain.card import Card
from cardforge.domain.feature import (
    TextBlockFeature,
    QRCodeFeature,
    PatternFeature,
    LogoFeature,
    FrameFeature,
)
from cardforge.assets.svg_utils import (
    svg_header,
    svg_footer,
    svg_rect,
    svg_text,
    svg_image,
    svg_group,
    svg_comment,
    sanitize_svg_id,
)
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.preview.theme import Theme


def render_face_preview_svg(
    card: Card,
    face_id: str,
    generated_assets: GeneratedAssets,
    output_path: Path,
    theme: Theme = None,
) -> Path:
    """Render a face preview as an SVG file.

    Args:
        card: The Card domain object.
        face_id: Which face to render (front, back).
        generated_assets: Previously generated assets (QR, patterns).
        output_path: Where to save the preview SVG.
        theme: Visual theme (colors, fonts). Created from card materials if None.

    Returns:
        The output path.

    Raises:
        ValueError: If face_id doesn't exist.
    """
    face = card.get_face(face_id)
    if face is None:
        raise ValueError(f"Face '{face_id}' not found in card '{card.id}'")

    if theme is None:
        theme = Theme.from_materials(card.materials)

    w = card.width
    h = card.height
    r = card.corner_radius

    lines = []
    lines.append(svg_comment(f"CardForge preview — {card.name} — {face_id}"))
    lines.append(svg_header(w, h))

    # Card base
    lines.append(svg_rect(0, 0, w, h, rx=r, fill=theme.card_base_color))

    # Get sorted features
    features = face.sorted_features()

    # Build asset lookup: feature_id → relative path
    qr_map = {}
    for qr_path in generated_assets.qr_paths:
        # qr paths are like: assets/qr_vcard_qr.svg
        qr_map[qr_path.stem] = qr_path

    pattern_map = {}
    for pat_path in generated_assets.pattern_paths:
        # pattern paths are like: assets/pattern_front_bg_monogram.svg
        pattern_map[pat_path.stem] = pat_path

    for feature in features:
        if not feature.visible:
            continue

        color = theme.get_color(feature.material)
        fx = feature.position.x
        fy = feature.position.y
        fw = feature.size.width
        fh = feature.size.height
        fid = sanitize_svg_id(feature.id)

        if isinstance(feature, PatternFeature):
            # Use image reference to pattern asset
            stem = f"pattern_{feature.face}_{feature.id}"
            if stem in pattern_map:
                rel_path = _relative_to_preview(pattern_map[stem], output_path)
                lines.append(svg_image(fx, fy, w, h, rel_path))

        elif isinstance(feature, QRCodeFeature):
            stem = f"qr_{feature.id}"
            if stem in qr_map:
                rel_path = _relative_to_preview(qr_map[stem], output_path)
                qr_size = feature.size.width or 24
                lines.append(svg_image(fx, fy, qr_size, qr_size, rel_path))

        elif isinstance(feature, TextBlockFeature):
            # Render each line
            for i, line in enumerate(feature.lines):
                ly = fy + (i + 1) * feature.font_size * feature.line_height
                lines.append(svg_text(
                    fx, ly, line,
                    font_family=feature.font,
                    font_size=feature.font_size,
                    font_weight=feature.font_style,
                    fill=color,
                ))

        elif isinstance(feature, FrameFeature):
            # Render as border rect
            lines.append(svg_rect(
                0, 0, w, h, rx=r,
                fill="none",
                stroke=color,
                stroke_width=feature.frame_width,
            ))

        elif isinstance(feature, LogoFeature):
            # Placeholder rect for logo
            logo_w = feature.size.width or 20
            logo_h = feature.size.height or 20
            lines.append(svg_rect(
                fx, fy, logo_w, logo_h,
                fill=color, rx=2,
            ))
            lines.append(svg_text(
                fx + logo_w / 2, fy + logo_h / 2,
                "LOGO", font_size=3, fill=theme.card_base_color,
                text_anchor="middle",
            ))

    lines.append(svg_footer())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    return output_path


def _relative_to_preview(asset_path: Path, preview_path: Path) -> str:
    """Compute a relative path from preview dir to an asset."""
    try:
        return "../assets/" + asset_path.name
    except ValueError:
        return str(asset_path)
