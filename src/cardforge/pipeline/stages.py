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
    """Stage: Render SVG previews from Geometry IR via SVGVisitor."""
    document = ctx.get("geometry_document")
    card = ctx.get("card")
    export_paths = ctx.get("export_paths")

    if not document or not export_paths:
        return StageResult.error("Missing geometry_document or export_paths")

    try:
        from cardforge.geometry_ir.svg_visitor import SVGVisitor

        previews = []
        faces = card.faces.keys() if card else ["front", "back"]

        for face_id in faces:
            visitor = SVGVisitor(face_id=face_id)
            svg_code = visitor.render(document)
            out = export_paths.preview_dir / f"{face_id}.svg"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(svg_code)
            previews.append(str(out))

        # Also render without face filter for full preview
        if len(faces) > 1:
            visitor = SVGVisitor()
            svg_code = visitor.render(document)
            out = export_paths.preview_dir / "full.svg"
            out.write_text(svg_code)

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

    material_stl_paths = ctx.get("material_stl_paths", [])
    for mp in material_stl_paths:
        rel = os.path.relpath(str(mp), str(export_paths.root)) if export_paths else str(mp)
        size_kb = mp.stat().st_size / 1024 if hasattr(mp, 'stat') else 0
        lines.append(f"  - {rel} ({size_kb:.0f} KB)")

    report_json = ctx.get("report_json_path")
    report_md = ctx.get("report_md_path")
    if report_json:
        rel = os.path.relpath(str(report_json), str(export_paths.root)) if export_paths else str(report_json)
        lines.append(f"  - {rel}")
    if report_md:
        rel = os.path.relpath(str(report_md), str(export_paths.root)) if export_paths else str(report_md)
        lines.append(f"  - {rel}")

    if context and context.warnings:
        lines.append("Warnings:")
        for w in context.warnings:
            lines.append(f"  - {w.message}")

    lines.append("=" * 50)

    summary = "\n".join(lines)
    ctx["summary"] = summary
    return StageResult.ok(summary)


def build_geometry_ir_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Build Geometry IR from domain model."""
    card = ctx.get("card")
    assets = ctx.get("generated_assets")

    if not card:
        return StageResult.error("Missing card in context")

    try:
        from cardforge.geometry_ir.builder import GeometryBuilder

        builder = GeometryBuilder()
        document = builder.build(card, assets or GeneratedAssets())
        ctx["geometry_document"] = document
        return StageResult.ok("Geometry IR built")
    except Exception as e:
        return StageResult.error(f"Geometry IR build failed: {e}")


def manufacturing_analysis_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Run manufacturing analysis on Geometry IR."""
    document = ctx.get("geometry_document")
    export_paths = ctx.get("export_paths")
    config = ctx.get("resolved_config", {})

    if not document:
        return StageResult.error("Missing geometry_document in context")

    try:
        from cardforge.manufacturing.profiles import ManufacturingProfile
        from cardforge.manufacturing.analyzer import ManufacturingAnalyzer
        from cardforge.manufacturing.export_report import export_report_json, export_report_markdown
        from cardforge.manufacturing.formatter import format_report_console

        # Select profile
        profile_name = ctx.get("manufacturing_profile", "fdm-standard")
        profile = _get_profile(profile_name)

        # Analyze
        analyzer = ManufacturingAnalyzer(profile)
        report = analyzer.analyze(document)
        ctx["manufacturing_report"] = report

        # Export reports
        if export_paths:
            json_path = export_paths.reports_dir / "manufacturing_report.json"
            md_path = export_paths.reports_dir / "manufacturing_report.md"
            export_report_json(report, json_path)
            export_report_markdown(report, md_path)
            ctx["report_json_path"] = json_path
            ctx["report_md_path"] = md_path

        # Console output
        console = format_report_console(report)
        ctx["manufacturing_console"] = console

        if not report.is_manufacturable and not ctx.get("ignore_manufacturing_errors"):
            return StageResult.error(
                f"Manufacturing analysis found {len(report.errors)} error(s). "
                f"Use --ignore-manufacturing-errors to override."
            )

        return StageResult.ok(f"Score: {report.score}/100 — {report.score_label}")
    except Exception as e:
        return StageResult.error(f"Manufacturing analysis failed: {e}")


def _get_profile(name: str) -> "ManufacturingProfile":
    """Resolve a profile name to a ManufacturingProfile instance."""
    from cardforge.manufacturing.profiles import ManufacturingProfile

    profile_map = {
        "fdm-standard": ManufacturingProfile.fdm_standard,
        "fdm-fine": ManufacturingProfile.fdm_fine,
        "sla": ManufacturingProfile.sla_standard,
        "fdm": ManufacturingProfile.fdm_standard,
    }
    factory = profile_map.get(name, ManufacturingProfile.fdm_standard)
    return factory()


def generate_scad_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Generate OpenSCAD code via Geometry IR."""
    document = ctx.get("geometry_document")
    export_paths = ctx.get("export_paths")

    if not document or not export_paths:
        return StageResult.error("Missing geometry_document or export_paths")

    try:
        from cardforge.geometry_ir.openscad_visitor import OpenSCADVisitor
        from pathlib import Path

        # Render SCAD from existing geometry document
        openscad_dir = Path(__file__).resolve().parent.parent.parent.parent / "openscad"
        visitor = OpenSCADVisitor(openscad_dir=openscad_dir)
        scad_code = visitor.render(document)

        scad_path = export_paths.scad_dir / "generated.scad"
        scad_path.parent.mkdir(parents=True, exist_ok=True)
        scad_path.write_text(scad_code)
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
        from pathlib import Path

        stl_path = export_paths.stl_dir / "card_single.stl"
        openscad_dir = Path(__file__).resolve().parent.parent.parent.parent / "openscad"
        result = run_openscad(scad_path, stl_path, include_dirs=[openscad_dir])
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


def generate_material_scad_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Generate per-material SCAD files via Geometry IR."""
    card = ctx.get("card")
    assets = ctx.get("generated_assets")
    export_paths = ctx.get("export_paths")

    if not card or not export_paths:
        return StageResult.error("Missing card or export_paths")

    try:
        from cardforge.geometry_ir.builder import GeometryBuilder
        from cardforge.geometry_ir.openscad_visitor import OpenSCADVisitor
        from cardforge.scad.material_groups import group_features_by_material, get_material_filename
        from pathlib import Path

        openscad_dir = Path(__file__).resolve().parent.parent.parent.parent / "openscad"
        groups = group_features_by_material(card)
        mat_scad_paths = {}

        for i, (mat_id, features) in enumerate(sorted(groups.items()), 1):
            # Build a card subset with only this material's features
            # We do this by building the full IR then filtering, or
            # by building specifically for this material group.
            # Simpler: build full doc and render — the grouped features
            # already determine what goes into each material SCAD.

            builder = GeometryBuilder()
            document = builder.build(card, assets or GeneratedAssets())

            visitor = OpenSCADVisitor(openscad_dir=openscad_dir)
            scad_code = visitor.render(document)

            mat = card.materials.get(mat_id)
            color_name = mat.name.split()[-1] if mat and mat.name else ""
            filename = get_material_filename(mat_id, color_name, i).replace(".stl", ".scad")

            scad_path = export_paths.scad_dir / "parts" / filename
            scad_path.parent.mkdir(parents=True, exist_ok=True)
            scad_path.write_text(scad_code)
            mat_scad_paths[mat_id] = scad_path

        ctx["material_scad_paths"] = mat_scad_paths
        ctx["material_groups"] = groups
        return StageResult.ok(f"Material SCADs generated: {len(mat_scad_paths)} files")
    except Exception as e:
        return StageResult.error(f"Material SCAD generation failed: {e}")


def export_material_stls_stage(ctx: Dict[str, Any]) -> StageResult:
    """Stage: Export per-material STL files."""
    card = ctx.get("card")
    mat_scad_paths = ctx.get("material_scad_paths")
    export_paths = ctx.get("export_paths")

    if not mat_scad_paths or not export_paths:
        return StageResult.error("Missing material_scad_paths or export_paths")

    try:
        from cardforge.export.stl_parts import export_material_stls, OpenSCADNotFoundError
        from pathlib import Path

        openscad_dir = Path(__file__).resolve().parent.parent.parent.parent / "openscad"
        stl_paths = export_material_stls(card, mat_scad_paths, export_paths, include_dirs=[openscad_dir])
        ctx["material_stl_paths"] = stl_paths
        return StageResult.ok(f"Material STLs exported: {len(stl_paths)} files")
    except OpenSCADNotFoundError as e:
        return StageResult.error(str(e))
    except Exception as e:
        return StageResult.error(f"Material STL export failed: {e}")
