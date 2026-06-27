"""Pipeline stages — concrete stage implementations for CardForge build."""

import os
from pathlib import Path
from typing import Any, Dict

from cardforge.config.loader import load_config
from cardforge.config.validator import validate_config, ValidationError
from cardforge.config.resolver import resolve_config
from cardforge.domain.factory import create_card_from_config, FactoryError
from cardforge.domain.build_context import BuildContext
from cardforge.domain.card import Card
from cardforge.assets.asset_manager import generate_assets, GeneratedAssets
from cardforge.preview.svg_renderer import render_face_preview_svg
from cardforge.preview.theme import Theme
from cardforge.export.paths import prepare_export_paths, ExportPaths
from cardforge.pipeline.orchestrator import StageResult


def load_config_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Load config from file path."""
    config_path = ctx.get("config_path")
    if not config_path:
        return StageResult.error("No config_path in context")
    try:
        ctx["raw_config"] = load_config(config_path)
        return StageResult.ok(f"Loaded {config_path}")
    except Exception as e:
        return StageResult.error(f"Load failed: {e}")


def validate_config_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Validate raw config."""
    raw = ctx.get("raw_config")
    if not raw:
        return StageResult.error("No raw_config in context")
    try:
        ctx["validated_config"] = validate_config(raw)
        return StageResult.ok("Config valid")
    except ValidationError as e:
        return StageResult.error(f"Validation failed: {e}")


def resolve_config_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Resolve template variables."""
    validated = ctx.get("validated_config")
    if not validated:
        return StageResult.error("No validated_config in context")
    try:
        ctx["resolved_config"] = resolve_config(validated)
        return StageResult.ok("Variables resolved")
    except Exception as e:
        return StageResult.error(f"Resolution failed: {e}")


def create_domain_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Create domain objects from resolved config."""
    resolved = ctx.get("resolved_config")
    if not resolved:
        return StageResult.error("No resolved_config in context")

    context = BuildContext()
    ctx["build_context"] = context

    try:
        card = create_card_from_config(resolved, context)
        ctx["card"] = card
        msg = f"Card created: {card.name} ({card.object_type})"
        if context.warnings:
            msg += f" — {len(context.warnings)} warning(s)"
        return StageResult.ok(msg)
    except FactoryError as e:
        return StageResult.error(f"Domain creation failed: {e}")


def prepare_exports_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Prepare export directory structure."""
    config = ctx.get("resolved_config", {})
    project_name = config.get("project", {}).get("name", "untitled")

    base_dir = Path(ctx.get("exports_dir", "exports"))
    try:
        export_paths = prepare_export_paths(project_name, base_dir=base_dir)
        ctx["export_paths"] = export_paths
        return StageResult.ok(f"Export dirs ready: {export_paths.root}")
    except Exception as e:
        return StageResult.error(f"Export preparation failed: {e}")


def generate_assets_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Generate derived assets (QR, patterns)."""
    card = ctx.get("card")
    config = ctx.get("resolved_config", {})
    export_paths = ctx.get("export_paths")

    if not card or not export_paths:
        return StageResult.error("Missing card or export_paths")

    try:
        assets = generate_assets(card, config, export_paths)
        ctx["generated_assets"] = assets
        count = len(assets.all_paths)
        return StageResult.ok(f"Generated {count} asset(s)")
    except Exception as e:
        return StageResult.error(f"Asset generation failed: {e}")


def render_preview_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Render SVG previews for each face."""
    card = ctx.get("card")
    assets = ctx.get("generated_assets")
    export_paths = ctx.get("export_paths")

    if not card or not export_paths:
        return StageResult.error("Missing card or export_paths")

    theme = Theme.from_materials(card.materials)
    previews = []

    try:
        for face_id in card.faces:
            out = export_paths.preview_dir / f"{face_id}.svg"
            render_face_preview_svg(card, face_id, assets or GeneratedAssets(), out, theme)
            previews.append(str(out))

        ctx["preview_paths"] = previews
        return StageResult.ok(f"Rendered {len(previews)} preview(s)")
    except Exception as e:
        return StageResult.error(f"Preview failed: {e}")


def build_summary_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Print build summary."""
    card = ctx.get("card")
    config = ctx.get("resolved_config", {})
    export_paths = ctx.get("export_paths")
    generated = ctx.get("generated_assets", GeneratedAssets())
    context = ctx.get("build_context")

    lines = []
    lines.append("")
    lines.append("=" * 50)
    lines.append("CardForge build")
    project_name = config.get("project", {}).get("name", "Untitled")
    lines.append(f"Project: {project_name}")
    if export_paths:
        lines.append(f"Exports: {export_paths.root}")
    lines.append("Generated:")

    if generated:
        for p in generated.all_paths:
            rel = os.path.relpath(str(p), str(export_paths.root)) if export_paths else str(p)
            lines.append(f"  - {rel}")

    previews = ctx.get("preview_paths", [])
    for p in previews:
        rel = os.path.relpath(p, str(export_paths.root)) if export_paths else p
        lines.append(f"  - {rel}")

    scad_path = ctx.get("scad_path")
    if scad_path:
        rel = os.path.relpath(str(scad_path), str(export_paths.root)) if export_paths else str(scad_path)
        lines.append(f"  - {rel}")

    stl_path = ctx.get("stl_path")
    if stl_path:
        rel = os.path.relpath(str(stl_path), str(export_paths.root)) if export_paths else str(stl_path)
        size_kb = stl_path.stat().st_size / 1024 if hasattr(stl_path, 'stat') else 0
        lines.append(f"  - {rel} ({size_kb:.0f} KB)")

    if context and context.warnings:
        lines.append("Warnings:")
        for w in context.warnings:
            lines.append(f"  - {w.message}")

    lines.append("=" * 50)

    summary = "\n".join(lines)
    ctx["summary"] = summary
    return StageResult.ok(summary)


def generate_scad_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Generate OpenSCAD code from domain model."""
    card = ctx.get("card")
    assets = ctx.get("generated_assets")
    export_paths = ctx.get("export_paths")

    if not card or not export_paths:
        return StageResult.error("Missing card or export_paths")

    try:
        from cardforge.scad.generator import generate_scad
        scad_path = generate_scad(card, assets or GeneratedAssets(), export_paths)
        ctx["scad_path"] = scad_path
        return StageResult.ok(f"SCAD generated: {scad_path}")
    except Exception as e:
        return StageResult.error(f"SCAD generation failed: {e}")


def export_stl_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Export single STL via OpenSCAD CLI."""
    scad_path = ctx.get("scad_path")
    export_paths = ctx.get("export_paths")

    if not scad_path or not export_paths:
        return StageResult.error("Missing scad_path or export_paths")

    try:
        from cardforge.export.openscad_cli import find_openscad, run_openscad, OpenSCADNotFoundError

        stl_path = export_paths.stl_dir / "card_single.stl"
        result = run_openscad(scad_path, stl_path)
        if result.success:
            ctx["stl_path"] = stl_path
            size_kb = stl_path.stat().st_size / 1024 if stl_path.exists() else 0
            return StageResult.ok(f"STL exported: {stl_path} ({size_kb:.0f} KB)")
        else:
            return StageResult.error(f"OpenSCAD failed: {result.stderr}")

    except OpenSCADNotFoundError as e:
        return StageResult.error(str(e))
    except Exception as e:
        return StageResult.error(f"STL export failed: {e}")
