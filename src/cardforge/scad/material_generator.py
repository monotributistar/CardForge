"""Material SCAD Generator — generates per-material .scad files for multi-color STL."""

from pathlib import Path
from typing import Dict, List, Optional

from cardforge.domain.card import Card
from cardforge.domain.feature import (
    Feature, TextBlockFeature, QRCodeFeature, PatternFeature, LogoFeature, FrameFeature,
)
from cardforge.domain.geometry import ReliefMode
from cardforge.domain.material import Material
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.export.paths import ExportPaths
from cardforge.scad.writer import ScadWriter


def generate_material_scad_files(
    card: Card,
    material_groups: Dict[str, List[Feature]],
    generated_assets: GeneratedAssets,
    export_paths: ExportPaths,
    openscad_dir: Optional[Path] = None,
) -> Dict[str, Path]:
    """Generate a .scad file for each material group.

    Args:
        card: Populated Card domain object.
        material_groups: Features grouped by material (from group_features_by_material).
        generated_assets: Generated SVG assets (QR, patterns).
        export_paths: Export directory structure.
        openscad_dir: Path to openscad/ directory for include resolution.

    Returns:
        Dict mapping material_id to the generated .scad file path.
    """
    if openscad_dir is None:
        openscad_dir = Path(__file__).resolve().parent.parent.parent.parent / "openscad"
    parts_dir = export_paths.scad_dir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    # Build asset lookups
    qr_map = {p.stem: p for p in generated_assets.qr_paths}
    pattern_map = {p.stem: p for p in generated_assets.pattern_paths}

    # Get color names for filenames
    filename_map = {}
    for i, mat_id in enumerate(sorted(material_groups.keys()), 1):
        mat = card.materials.get(mat_id)
        color_name = mat.name.split()[-1] if mat and mat.name else ""
        from cardforge.scad.material_groups import get_material_filename
        filename_map[mat_id] = get_material_filename(mat_id, color_name, i)

    results = {}
    for mat_id, features in material_groups.items():
        scad_path = _generate_single_material_scad(
            card, mat_id, features, qr_map, pattern_map,
            parts_dir, filename_map.get(mat_id, f"{mat_id}.scad"),
            openscad_dir,
        )
        results[mat_id] = scad_path

    return results


def _generate_single_material_scad(
    card: Card,
    mat_id: str,
    features: List[Feature],
    qr_map: dict,
    pattern_map: dict,
    parts_dir: Path,
    filename: str,
    openscad_dir: Path,
) -> Path:
    """Generate a .scad file for a single material."""
    w = ScadWriter()

    # Header
    w.comment(f"CardForge — Material: {mat_id}")
    w.comment(f"Project: {card.name}")
    w.comment("Do not edit manually")
    w.blank_line()
    w.include(str(openscad_dir.resolve() / "main.scad"))
    w.blank_line()

    half_w = card.width / 2
    half_h = card.height / 2
    thickness = card.thickness

    # If this is the base material, render card_base
    if mat_id == "base":
        w.section("Card Base")
        w.module_call(
            "card_base",
            width=card.width, height=card.height,
            thickness=card.thickness, radius=card.corner_radius,
        )
        w.blank_line()

    # Render features for both faces
    for face_id in ("front", "back"):
        face = card.get_face(face_id)
        if face is None:
            continue
        face_features = [f for f in features if f.face == face_id]
        if not face_features:
            continue

        w.section(f"{face_id.capitalize()} Face — Material: {mat_id}")

        is_back = (face_id == "back")
        if is_back:
            w.mirror_z()

        for feature in face_features:
            if not feature.visible:
                continue

            scad_x = feature.position.x - half_w
            scad_y = half_h - feature.position.y
            z_pos = thickness
            relief = feature.relief
            mode = relief.mode

            if isinstance(feature, QRCodeFeature):
                stem = f"qr_{feature.id}"
                if stem in qr_map:
                    rel_path = f"../../assets/{qr_map[stem].name}"
                    qr_size = feature.size.width or 24
                    scad_x += qr_size / 2
                    scad_y -= qr_size / 2
                    height_val = relief.height if mode == ReliefMode.EMBOSS else 0.4
                    w.comment(f"QR: {feature.id}")
                    w.module_call(
                        "svg_emboss_layer",
                        file=rel_path, x=scad_x, y=scad_y, z=z_pos,
                        height=height_val, scale_factor=qr_size,
                    )

            elif isinstance(feature, PatternFeature):
                stem = f"pattern_{face_id}_{feature.id}"
                if stem in pattern_map:
                    rel_path = f"../../assets/{pattern_map[stem].name}"
                    if mode == ReliefMode.DEBOSS and mat_id == "base":
                        depth_val = relief.depth or 0.2
                        w.comment(f"Pattern deboss: {feature.id}")
                        w.difference()
                        w.module_call(
                            "card_base", width=card.width, height=card.height,
                            thickness=card.thickness, radius=card.corner_radius,
                        )
                        w.module_call(
                            "svg_emboss_layer", file=rel_path,
                            x=0, y=0, z=thickness - depth_val,
                            height=depth_val, scale_factor=card.width,
                        )
                        w.close_block()
                    else:
                        height_val = relief.height if mode == ReliefMode.EMBOSS else 0.2
                        w.comment(f"Pattern: {feature.id}")
                        w.module_call(
                            "svg_emboss_layer", file=rel_path,
                            x=0, y=0, z=thickness,
                            height=height_val, scale_factor=card.width,
                        )

            elif isinstance(feature, TextBlockFeature):
                height_val = relief.height if mode == ReliefMode.EMBOSS else 0.4
                w.comment(f"Text: {feature.id}")
                for i, line in enumerate(feature.lines):
                    ly = scad_y - i * feature.font_size * feature.line_height
                    halign = "left"
                    if feature.align == "center":
                        halign = "center"
                    elif feature.align == "right":
                        halign = "right"
                    w.module_call(
                        "text_emboss_layer",
                        text_value=line, x=scad_x, y=ly, z=z_pos,
                        font_size=feature.font_size, height=height_val,
                        font_name=feature.font, halign=halign, valign="top",
                    )

            elif isinstance(feature, LogoFeature):
                logo_w = feature.size.width or 20
                logo_h = feature.size.height or 20
                height_val = relief.height if mode == ReliefMode.EMBOSS else 0.5
                w.comment(f"Logo placeholder: {feature.id}")
                w.translate(scad_x, scad_y, z_pos)
                w.line(f"cube([{logo_w}, {logo_h}, {height_val}]);")
                w.close_block()

        if is_back:
            w.close_block()  # mirror

        w.blank_line()

    # Write
    scad_path = parts_dir / filename.replace(".stl", ".scad")
    scad_path.write_text(w.build())
    return scad_path
