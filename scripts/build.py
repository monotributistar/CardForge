#!/usr/bin/env python3
"""CardForge build script — end-to-end pipeline from JSON config to preview/SCAD/STL."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cardforge.pipeline.orchestrator import Pipeline
from cardforge.pipeline.stages import (
    load_config_stage,
    validate_config_stage,
    resolve_config_stage,
    create_domain_stage,
    prepare_exports_stage,
    generate_assets_stage,
    render_preview_stage,
    build_geometry_ir_stage,
    manufacturing_analysis_stage,
    generate_scad_stage,
    export_stl_stage,
    generate_material_scad_stage,
    export_material_stls_stage,
    build_summary_stage,
)


def build(
    config_path: str,
    exports_dir: str = "exports",
    stl: bool = False,
    parts: bool = False,
    profile: str = "fdm-standard",
    ignore_errors: bool = False,
    report_only: bool = False,
) -> int:
    """Run the full CardForge pipeline.

    Args:
        config_path: Path to JSON config file.
        exports_dir: Directory for build outputs.
        stl: Generate single STL.
        parts: Generate per-material STLs.
        profile: Manufacturing profile (fdm-standard, fdm-fine, sla).
        ignore_errors: Continue even if manufacturing errors found.
        report_only: Only generate report, no STL.

    Returns:
        0 on success, 1 on failure.
    """
    pipeline = Pipeline()
    pipeline.add_stage("load", load_config_stage)
    pipeline.add_stage("validate", validate_config_stage)
    pipeline.add_stage("resolve", resolve_config_stage)
    pipeline.add_stage("domain", create_domain_stage)
    pipeline.add_stage("exports", prepare_exports_stage)
    pipeline.add_stage("assets", generate_assets_stage)
    pipeline.add_stage("preview", render_preview_stage)

    # Build Geometry IR (always, needed for manufacturing analysis)
    pipeline.add_stage("geometry_ir", build_geometry_ir_stage)

    # Manufacturing analysis always runs
    pipeline.add_stage("manufacturing", manufacturing_analysis_stage)

    if not report_only:
        if stl:
            pipeline.add_stage("scad", generate_scad_stage)
            pipeline.add_stage("stl", export_stl_stage)

        if parts:
            pipeline.add_stage("material_scad", generate_material_scad_stage)
            pipeline.add_stage("material_stl", export_material_stls_stage)

    pipeline.add_stage("summary", build_summary_stage)

    result = pipeline.run({
        "config_path": config_path,
        "exports_dir": exports_dir,
        "manufacturing_profile": profile,
        "ignore_manufacturing_errors": ignore_errors,
    })

    if result.success:
        summary = result.context.get("summary", "")
        console = result.context.get("manufacturing_console", "")
        if console:
            print(console)
        if summary:
            print(summary)
        return 0
    else:
        print(f"Build failed: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/build.py <config.json> [options]", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  --stl                    Generate single STL", file=sys.stderr)
        print("  --parts                  Generate per-material STLs", file=sys.stderr)
        print("  --profile <name>         Manufacturing profile (fdm-standard, fdm-fine, sla)", file=sys.stderr)
        print("  --ignore-manufacturing-errors  Continue even with manufacturing errors", file=sys.stderr)
        print("  --report-only            Only generate report, no STL", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]
    args = sys.argv[2:]

    generate_stl = "--stl" in args
    generate_parts = "--parts" in args
    report_only = "--report-only" in args
    ignore_errors = "--ignore-manufacturing-errors" in args

    # Extract profile value
    profile = "fdm-standard"
    if "--profile" in args:
        idx = args.index("--profile")
        if idx + 1 < len(args):
            profile = args[idx + 1]

    sys.exit(build(
        config_file,
        stl=generate_stl,
        parts=generate_parts,
        profile=profile,
        ignore_errors=ignore_errors,
        report_only=report_only,
    ))
