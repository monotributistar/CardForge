"""Prototype build logic — orchestrates the full prototype loop."""

import json
import os
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def prototype_build(
    document_path: str,
    exports_dir: str = "exports",
    clean: bool = False,
    open_preview: bool = False,
    watch: bool = False,
) -> int:
    """Run the full prototype loop on a .cardforge.json document.

    Returns 0 on success, 1 on failure.
    """
    from cardforge.document.loader import load_document, is_document_file
    from cardforge.document.adapter import resolve_document_variables, adapt_to_legacy_config
    from cardforge.document.print_readme import generate_print_readme

    # Load
    try:
        doc = load_document(document_path)
    except Exception as e:
        print(f"Failed to load document: {e}", file=sys.stderr)
        return 1

    # Resolve variables
    doc = resolve_document_variables(doc)

    if not doc.objects:
        print("No objects in document", file=sys.stderr)
        return 1

    # Clean if requested
    safe_name = doc.metadata.id or "untitled"
    export_root = Path(exports_dir) / safe_name
    if clean and export_root.exists():
        shutil.rmtree(export_root)

    # Adapt to legacy config
    legacy_config = adapt_to_legacy_config(doc)

    # Export resolved document
    doc_dir = export_root / "document"
    doc_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = doc_dir / "resolved.cardforge.json"
    resolved_path.write_text(json.dumps(legacy_config, indent=2))

    # Run the build pipeline
    from cardforge.pipeline.orchestrator import Pipeline
    from cardforge.pipeline.stages import (
        load_config_stage, validate_config_stage, resolve_config_stage,
        create_domain_stage, prepare_exports_stage, generate_assets_stage,
        build_geometry_ir_stage, render_preview_stage,
        manufacturing_analysis_stage, generate_scad_stage,
        export_stl_stage, generate_material_scad_stage,
        export_material_stls_stage, build_summary_stage,
    )

    pipeline = Pipeline()
    pipeline.add_stage("load_pipe", load_config_stage)
    pipeline.add_stage("validate", validate_config_stage)
    pipeline.add_stage("resolve", resolve_config_stage)
    pipeline.add_stage("domain", create_domain_stage)
    pipeline.add_stage("exports", prepare_exports_stage)
    pipeline.add_stage("assets", generate_assets_stage)
    pipeline.add_stage("geometry_ir", build_geometry_ir_stage)
    pipeline.add_stage("preview", render_preview_stage)
    pipeline.add_stage("manufacturing", manufacturing_analysis_stage)

    if doc.exports.single_stl:
        pipeline.add_stage("scad", generate_scad_stage)
        pipeline.add_stage("stl", export_stl_stage)

    if doc.exports.color_separated_stl:
        pipeline.add_stage("material_scad", generate_material_scad_stage)
        pipeline.add_stage("material_stl", export_material_stls_stage)

    pipeline.add_stage("summary", build_summary_stage)

    # Write legacy config to temp file for pipeline
    tmp_config = Path(exports_dir) / "_temp_config.json"
    tmp_config.write_text(json.dumps(legacy_config))

    result = pipeline.run({
        "config_path": str(tmp_config),
        "exports_dir": exports_dir,
        "manufacturing_profile": doc.manufacturing.profile,
    })

    tmp_config.unlink(missing_ok=True)

    # Generate print README
    report = result.context.get("manufacturing_report")
    if report:
        stl_paths = []
        single = result.context.get("stl_path")
        if single and single.exists():
            stl_paths.append(single)
        material_stls = result.context.get("material_stl_paths", [])
        stl_paths.extend(material_stls)

        print_dir = export_root / "print"
        print_dir.mkdir(parents=True, exist_ok=True)
        generate_print_readme(doc.metadata.name or "Untitled", report, stl_paths,
                              print_dir / "README_PRINT.md")

    # Console output
    console = result.context.get("manufacturing_console", "")
    if console:
        print(console)
    summary = result.context.get("summary", "")
    if summary:
        print(summary)

    # Open preview
    if open_preview:
        preview_dir = export_root / "preview"
        if preview_dir.exists():
            front = preview_dir / "front.svg"
            if front.exists():
                os.system(f"open {front}")

    return 0 if result.success else 1


def watch_loop(document_path: str, exports_dir: str = "exports",
               clean: bool = True, open_preview: bool = False):
    """Simple file-watch loop for prototype iteration.

    Polls mtime every second and rebuilds on change.
    """
    last_mtime = 0
    print(f"Watching {document_path} for changes... (Ctrl+C to stop)")
    while True:
        try:
            mtime = os.path.getmtime(document_path)
            if mtime != last_mtime:
                last_mtime = mtime
                print(f"\n{'='*50}")
                print(f"Change detected — rebuilding...")
                print(f"{'='*50}")
                prototype_build(document_path, exports_dir,
                                clean=clean, open_preview=open_preview)
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nWatch stopped.")
            break
        except Exception as e:
            print(f"Watch error: {e}", file=sys.stderr)
            time.sleep(1)
