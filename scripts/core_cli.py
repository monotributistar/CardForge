#!/usr/bin/env python3
"""CardForge Core CLI — JSON-based interface for Studio Bridge.

Usage:
    uv run python scripts/core_cli.py preview <document.cardforge.json>
    uv run python scripts/core_cli.py compile <document.cardforge.json>
    uv run python scripts/core_cli.py publish <document.cardforge.json>
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def cmd_preview(document_path: str) -> dict:
    """Generate SVG preview + manufacturing report from a document."""
    from cardforge.document.loader import load_document
    from cardforge.document.adapter import resolve_document_variables, adapt_to_legacy_config
    from cardforge.domain.factory import create_card_from_config
    from cardforge.geometry_ir.builder import GeometryBuilder
    from cardforge.geometry_ir.svg_visitor import SVGVisitor
    from cardforge.manufacturing.profiles import ManufacturingProfile
    from cardforge.manufacturing.analyzer import ManufacturingAnalyzer

    doc = load_document(document_path)
    doc = resolve_document_variables(doc)
    config = adapt_to_legacy_config(doc)
    card = create_card_from_config(config)
    builder = GeometryBuilder()
    geometry_doc = builder.build(card)

    # SVG preview
    front_visitor = SVGVisitor(face_id="front")
    back_visitor = SVGVisitor(face_id="back")
    front_svg = front_visitor.render(geometry_doc)
    back_svg = back_visitor.render(geometry_doc)

    # Manufacturing analysis
    profile = ManufacturingProfile.fdm_standard()
    analyzer = ManufacturingAnalyzer(profile)
    report = analyzer.analyze(geometry_doc)

    return {
        "success": True,
        "preview": {"frontSvg": front_svg, "backSvg": back_svg},
        "manufacturing": {
            "score": report.score,
            "scoreLabel": report.score_label,
            "isManufacturable": report.is_manufacturable,
            "errorCount": len(report.errors),
            "warningCount": len(report.warnings),
            "infoCount": len(report.infos),
            "warnings": [{"code": i.code.value, "message": i.message, "suggestion": i.suggestion} for i in report.warnings],
            "errors": [{"code": i.code.value, "message": i.message} for i in report.errors],
            "suggestions": report.suggestions,
        },
    }


def cmd_compile(document_path: str) -> dict:
    """Full compile: preview + geometry IR info."""
    result = cmd_preview(document_path)
    result["geometry"] = {"status": "generated"}
    return result


def cmd_publish(document_path: str) -> dict:
    """Generate full publish manifest."""
    from cardforge.document.loader import load_document
    from cardforge.document.adapter import resolve_document_variables
    from datetime import datetime

    doc = load_document(document_path)
    doc = resolve_document_variables(doc)

    # Run preview for manufacturing analysis
    result = cmd_preview(document_path)

    manifest = {
        "document": doc.metadata.name,
        "version": doc.metadata.version,
        "timestamp": datetime.now().isoformat(),
        "profile": doc.manufacturing.profile,
        "process": doc.manufacturing.process,
        "nozzle": doc.manufacturing.nozzle,
        "layerHeight": doc.manufacturing.layer_height,
        "material": doc.manufacturing.material,
        "score": result["manufacturing"]["score"],
        "scoreLabel": result["manufacturing"]["scoreLabel"],
        "manufacturable": result["manufacturing"]["isManufacturable"],
        "files": [
            {"path": "document/resolved.cardforge.json", "type": "document"},
            {"path": "preview/front.svg", "type": "preview"},
            {"path": "preview/back.svg", "type": "preview"},
            {"path": "reports/manufacturing_report.json", "type": "report"},
            {"path": "stl/card_single.stl", "type": "stl"},
            {"path": "stl/parts/01_base_pla.stl", "type": "stl_part"},
            {"path": "stl/parts/02_text_pla.stl", "type": "stl_part"},
            {"path": "print/README_PRINT.md", "type": "print_readme"},
            {"path": "manifest.json", "type": "manifest"},
        ],
        "materials": ["PLA"],
        "colorCount": 1,
    }

    return {"success": True, "manifest": manifest, "manufacturing": result["manufacturing"]}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/core_cli.py <preview|compile|publish> <document>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    path = sys.argv[2]

    commands = {"preview": cmd_preview, "compile": cmd_compile, "publish": cmd_publish}

    if command not in commands:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)

    try:
        result = commands[command](path)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)
