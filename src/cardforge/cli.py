"""CardForge CLI — build a document into a manufacturing package.

Usage:
    cardforge build <file.cardforge.json> [--out exports] [--profile fdm-standard]
                    [--no-stl] [--ignore-errors]
    cardforge validate <file.cardforge.json>
"""

from __future__ import annotations

import argparse
import sys


def build(args) -> int:
    from cardforge.pipeline.stages import build_pipeline

    pipeline = build_pipeline(export_stl=not args.no_stl)
    result = pipeline.run({
        "document_path": args.file,
        "exports_dir": args.out,
        "manufacturing_profile": args.profile,
        "ignore_manufacturing_errors": args.ignore_errors,
        "ignore_constraint_errors": args.ignore_errors,
        "asset_root": ".",
    })

    console = result.context.get("manufacturing_console")
    if console:
        print(console)
    for name, stage in result.stages.items():
        status = "✓" if stage.status == "ok" else "✗"
        print(f"{status} {name}: {stage.message}")
    if not result.success:
        print(f"\nBuild failed: {result.error}", file=sys.stderr)
        return 1
    return 0


def validate(args) -> int:
    from cardforge.document.loader import DocumentLoadError, load_document_v2
    from cardforge.document.schema_v2 import DocumentValidationError

    try:
        doc = load_document_v2(args.file)
    except (DocumentLoadError, DocumentValidationError) as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    features = sum(len(f.features) for f in doc.faces.values())
    print(f"OK: '{doc.meta.name}' — {len(doc.materials)} materials, "
          f"{features} features")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="cardforge")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="compile a document to 3MF/STL")
    b.add_argument("file")
    b.add_argument("--out", default="exports")
    b.add_argument("--profile", default="fdm-standard")
    b.add_argument("--no-stl", action="store_true")
    b.add_argument("--ignore-errors", action="store_true")
    b.set_defaults(fn=build)

    v = sub.add_parser("validate", help="validate a document")
    v.add_argument("file")
    v.set_defaults(fn=validate)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
