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

    if context and context.warnings:
        lines.append("Warnings:")
        for w in context.warnings:
            lines.append(f"  - {w.message}")

    lines.append("=" * 50)

    summary = "\n".join(lines)
    ctx["summary"] = summary
    return StageResult.ok(summary)
