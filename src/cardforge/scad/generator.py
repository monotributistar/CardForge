"""SCAD Generator — converts Card domain model to OpenSCAD code."""

import os
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
from cardforge.domain.geometry import ReliefMode
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.export.paths import ExportPaths
from cardforge.scad.writer import ScadWriter


def generate_scad(
    card: Card,
    generated_assets: GeneratedAssets,
    export_paths: ExportPaths,
    openscad_dir: Optional[Path] = None,
) -> Path:
    """Generate the OpenSCAD file from a Card domain object.

    Args:
        card: Populated Card domain object.
        generated_assets: Previously generated SVG assets.
        export_paths: Export directory paths.
        openscad_dir: Path to openscad/ directory for relative includes.
                      Defaults to project root openscad/.

    Returns:
        Path to the generated .scad file.
    """
    if openscad_dir is None:
        # Default: project root openscad/
        openscad_dir = Path(__file__).resolve().parent.parent.parent.parent / "openscad"

    writer = ScadWriter()

    # Header
    writer.comment("CardForge — Auto-generated OpenSCAD")
    writer.comment(f"Project: {card.name}")
    writer.comment("Do not edit manually — edit config JSON instead")
    writer.blank_line()

    # Include modules
    writer.include("main.scad")
    writer.blank_line()

    # Card base
    writer.section("Card Base")
    writer.module_call(
        "card_base",
        width=card.width,
        height=card.height,
        thickness=card.thickness,
        radius=card.corner_radius,
    )
    writer.blank_line()

    # Build asset lookup
    qr_map = {}
    for qr_path in generated_assets.qr_paths:
        qr_map[qr_path.stem] = qr_path
    pattern_map = {}
    for pat_path in generated_assets.pattern_paths:
        pattern_map[pat_path.stem] = pat_path

    # Front face features
    front = card.get_face("front")
    if front:
        writer.section("Front Face Features")
        _render_face_features(
            writer, card, front, "front",
            generated_assets, qr_map, pattern_map,
            is_back=False,
        )

    # Back face features (mirrored on z-axis, below the card)
    back = card.get_face("back")
    if back:
        writer.section("Back Face Features")
        _render_face_features(
            writer, card, back, "back",
            generated_assets, qr_map, pattern_map,
            is_back=True,
        )

    # Write file
    scad_path = export_paths.scad_dir / "generated.scad"
    scad_path.parent.mkdir(parents=True, exist_ok=True)
    scad_path.write_text(writer.build())
    return scad_path


def _render_face_features(
    writer: ScadWriter,
    card: Card,
    face,
    face_id: str,
    assets: GeneratedAssets,
    qr_map: dict,
    pattern_map: dict,
    is_back: bool,
) -> None:
    """Render all features for a face."""

    if is_back:
        # Back face: mirror below the card
        writer.mirror_z()

    features = face.sorted_features()
    half_w = card.width / 2
    half_h = card.height / 2
    thickness = card.thickness

    for feature in features:
        if not feature.visible:
            continue

        # Convert top-left Python coords to centered OpenSCAD coords
        scad_x = feature.position.x - half_w
        scad_y = half_h - feature.position.y

        # Z position: front on top, back already mirrored
        z_pos = thickness  # start above card surface for emboss

        fid = feature.id
        relief = feature.relief
        mode = relief.mode
        has_svg = False

        if isinstance(feature, QRCodeFeature):
            stem = f"qr_{feature.id}"
            if stem in qr_map:
                qr_path = qr_map[stem]
                rel_path = _relative_path(qr_path)
                qr_size = feature.size.width or 24

                # Center the QR at its position
                scad_x += qr_size / 2
                scad_y -= qr_size / 2

                height_val = relief.height if mode == ReliefMode.EMBOSS else 0.4
                writer.comment(f"QR: {fid}")
                writer.module_call(
                    "svg_emboss_layer",
                    file=rel_path,
                    x=scad_x,
                    y=scad_y,
                    z=z_pos,
                    height=height_val,
                    scale_factor=qr_size,
                )
                has_svg = True

        elif isinstance(feature, PatternFeature):
            stem = f"pattern_{face_id}_{feature.id}"
            if stem in pattern_map:
                pat_path = pattern_map[stem]
                rel_path = _relative_path(pat_path)

                # Pattern covers the whole face
                if mode == ReliefMode.DEBOSS:
                    # Deboss: subtract pattern from base
                    depth_val = relief.depth or 0.2
                    writer.comment(f"Pattern (deboss): {fid}")
                    writer.difference()
                    writer.module_call(
                        "card_base",
                        width=card.width,
                        height=card.height,
                        thickness=card.thickness,
                        radius=card.corner_radius,
                    )
                    writer.module_call(
                        "svg_emboss_layer",
                        file=rel_path,
                        x=0, y=0, z=thickness - depth_val,
                        height=depth_val,
                        scale_factor=card.width,
                    )
                    writer.close_block()
                else:
                    # Emboss: add pattern on top
                    height_val = relief.height if mode == ReliefMode.EMBOSS else 0.2
                    writer.comment(f"Pattern: {fid}")
                    writer.module_call(
                        "svg_emboss_layer",
                        file=rel_path,
                        x=0, y=0, z=thickness,
                        height=height_val,
                        scale_factor=card.width,
                    )
                has_svg = True

        elif isinstance(feature, TextBlockFeature):
            height_val = relief.height if mode == ReliefMode.EMBOSS else 0.4
            writer.comment(f"Text: {fid}")
            for i, line in enumerate(feature.lines):
                # Position each line
                ly = scad_y - i * feature.font_size * feature.line_height
                halign = "left"
                if feature.align == "center":
                    halign = "center"
                elif feature.align == "right":
                    halign = "right"
                writer.module_call(
                    "text_emboss_layer",
                    text_value=line,
                    x=scad_x,
                    y=ly,
                    z=z_pos,
                    font_size=feature.font_size,
                    height=height_val,
                    font_name=feature.font,
                    halign=halign,
                    valign="top",
                )

        elif isinstance(feature, LogoFeature):
            # Logo placeholder as small embossed rectangle
            logo_w = feature.size.width or 20
            logo_h = feature.size.height or 20
            height_val = relief.height if mode == ReliefMode.EMBOSS else 0.5
            writer.comment(f"Logo placeholder: {fid}")
            writer.translate(scad_x, scad_y, z_pos)
            writer.line(f"cube([{logo_w}, {logo_h}, {height_val}]);")
            writer.close_block()

        elif isinstance(feature, FrameFeature):
            # Frame as border — for MVP, just a comment
            writer.comment(f"Frame ({feature.frame_style}): {fid} — TODO: implement frame geometry")

    if is_back:
        writer.close_block()  # mirror


def _relative_path(asset_path: Path) -> str:
    """Convert asset path to a relative path from the scad directory.

    OpenSCAD resolves relative paths from the .scad file location.
    """
    return f"../assets/{asset_path.name}"
