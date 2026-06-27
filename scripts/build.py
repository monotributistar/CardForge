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
    generate_scad_stage,
    export_stl_stage,
    generate_material_scad_stage,
    export_material_stls_stage,
    build_summary_stage,
)


def build(config_path: str, exports_dir: str = "exports", stl: bool = False, parts: bool = False) -> int:
    """Run the full CardForge pipeline.

    Args:
        config_path: Path to JSON config file.
        exports_dir: Directory for build outputs.
        stl: If True, also generate SCAD and single STL.
        parts: If True, generate per-material SCAD and STL files.

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
    })

    if result.success:
        summary = result.context.get("summary", "")
        if summary:
            print(summary)
        return 0
    else:
        print(f"Build failed: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/build.py <config.json> [--stl] [--parts]", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]
    generate_stl = "--stl" in sys.argv
    generate_parts = "--parts" in sys.argv
    sys.exit(build(config_file, stl=generate_stl, parts=generate_parts))
