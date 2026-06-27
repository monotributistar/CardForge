#!/usr/bin/env python3
"""CardForge build script — end-to-end pipeline from JSON config to preview."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path
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
    build_summary_stage,
)


def build(config_path: str, exports_dir: str = "exports") -> int:
    """Run the full CardForge pipeline.

    Args:
        config_path: Path to JSON config file.
        exports_dir: Directory for build outputs.

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
        print("Usage: python scripts/build.py <config.json>", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]
    sys.exit(build(config_file))
