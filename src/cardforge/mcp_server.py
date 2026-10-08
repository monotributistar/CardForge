"""CardForge MCP server — drives the compiler from an AI agent.

Runs the kernel in-process (no HTTP server, no port, no CORS) and exposes the
same load → compile → analyze path the Studio uses, via `cardforge.service`.

The design constraint throughout: an agent's context is expensive, so nothing
returns geometry. A compile hands back the manufacturing verdict, the issues
with their fix suggestions, and where every feature landed in millimetres —
enough to judge and repair a design by arithmetic. The 3MF itself only ever
goes to disk, and only when the caller asks for a path.

Run:
    uv run python -m cardforge.mcp_server
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

from cardforge.service import (
    PROJECT_ROOT,
    analyze,
    compile_scene,
    feature_bounds_json,
    issues_json,
    load_document,
    materials_json,
    normalize_document,
    parts_json,
    report_json,
    safe_id,
    verdict,
    write_package,
)

server = MCPServer(
    name="cardforge",
    version="0.1.0",
    instructions=(
        "CardForge compiles a declarative JSON document into a 3D-printable "
        "multi-material object (cards, badges, tags, plates, signs). Call "
        "cardforge_guide first — it carries the authoring rules and the "
        "coordinate convention. Then iterate: write a document, "
        "cardforge_compile it, read the issues (each has a `suggestion`), fix, "
        "recompile. Export only once verdict.ready is true."
    ),
)


# ── Input handling ───────────────────────────────────────────────────

def _resolve_input(document: Optional[Dict[str, Any]],
                   path: Optional[str]) -> Dict[str, Any]:
    """Take the document inline or from disk — exactly one of the two."""
    if (document is None) == (path is None):
        raise ValueError("Pass exactly one of `document` (inline) or `path` (file)")
    if path is not None:
        p = Path(path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if not p.is_file():
            raise ValueError(f"No such document: {p}")
        return json.loads(p.read_text(encoding="utf-8"))
    return document


def _load(document, path):
    """→ (DocumentV2, None) or (None, structured validation failure)."""
    from cardforge.document.schema_v2 import DocumentValidationError

    try:
        raw = _resolve_input(document, path)
    except (ValueError, json.JSONDecodeError) as e:
        return None, {"ok": False, "stage": "input", "error": str(e)}
    try:
        return load_document(raw), None
    except DocumentValidationError as e:
        return None, {
            "ok": False, "stage": "validation",
            "error": "Document does not satisfy the v2 schema",
            "problems": e.errors[:20],
            "hint": "Call cardforge_schema(section='features') for the exact "
                    "shape of the feature type you got wrong.",
        }
    except (ValueError, KeyError, TypeError) as e:
        return None, {"ok": False, "stage": "load", "error": str(e)}


# ── Tools ────────────────────────────────────────────────────────────

@server.tool(
    description="Read this first. How to author a CardForge document: units, "
                "coordinate system, the workflow, and every feature type with "
                "its required fields (generated from the live schema).")
def cardforge_guide() -> Dict[str, Any]:
    from cardforge.document.schema_v2 import load_schema

    schema = load_schema()
    base = schema["$defs"]["featureBase"]
    branches = schema["$defs"]["feature"]["allOf"][1]["oneOf"]

    feature_types = {}
    for b in branches:
        t = b["properties"]["type"]["const"]
        required = [k for k in b.get("required", []) if k != "type"]
        optional = [k for k in b["properties"] if k != "type" and k not in required]
        feature_types[t] = {"required": required, "optional": optional}

    return {
        "units": "Every length is millimetres. Angles are degrees.",
        "coordinates": {
            "origin": "Top-left corner of the face, x right, y DOWN.",
            "anchor": "transform.x / transform.y is the TOP-LEFT corner of the "
                      "feature's own box, not its centre.",
            "verified": "A shape at transform {x:10, y:10} sized 20x8 occupies "
                        "x 10..30, y 10..18 in document space.",
            "qr": "A QR's anchor includes its quiet zone, so the printed "
                  "modules start at x+quietZone (default 2mm).",
            "back_face": "Back-face features are authored in back-face "
                         "document space; the compiler mirrors them. Author "
                         "the back as if you were looking straight at it.",
        },
        "document_skeleton": {
            "cardforge": "2.0",
            "meta": {"id": "kebab-case-id", "name": "Human name"},
            "object": {
                "outline": {"type": "rounded-rect", "width": 85,
                            "height": 54, "radius": 4},
                "thickness": 1.8,
            },
            "materials": [
                {"id": "base", "name": "Black PLA", "color": "#111111",
                 "role": "base", "slot": 1},
                {"id": "text", "name": "White PLA", "color": "#ffffff",
                 "role": "text", "slot": 2},
            ],
            "manufacturing": {"process": "fdm", "profile": "fdm-standard",
                              "nozzle": 0.4, "layerHeight": 0.2},
            "variables": {"name": "value — referenced as {{name}} anywhere"},
            "faces": {"front": {"features": []}, "back": {"features": []}},
        },
        "every_feature_needs": [k for k in base.get("required", [])],
        "feature_types": feature_types,
        "relief_modes": {
            "emboss": "raised — requires `height`",
            "deboss": "recessed — requires `depth`",
            "flush": "level with the surface, printed in another material — "
                     "requires `depth`. This is how you get flat colour.",
            "cut": "cut clean through",
            "deboss-backed": "recessed onto a floor of another material — "
                             "`depth`, `floorMaterial`, `floorThickness`",
        },
        "workflow": [
            "1. cardforge_examples — start from a document that already works "
            "instead of from nothing, when one is close to the request.",
            "2. cardforge_fonts — pick a family that actually exists, or the "
            "text silently falls back to another one.",
            "3. Write or edit the document.",
            "4. cardforge_compile and read `verdict`. THIS is the stopping "
            "condition: iterate while `verdict.ready` is false.",
            "5. Fix `verdict.blockers` — most carry a `suggestion` written as "
            "an instruction. Recompile.",
            "6. Check `featureBounds` to confirm nothing overflows the outline "
            "or overlaps something else.",
            "7. cardforge_export once `verdict.ready` is true.",
        ],
        "stopping_condition": {
            "use": "verdict.ready",
            "do_not_use": "manufacturing.score or manufacturing.errorCount",
            "why": "The manufacturing analyzer is one of three feedback "
                   "channels and cannot see the other two. A document whose "
                   "back face lost every feature to an illegal relief mode "
                   "still scores 100 and labels itself 'Excellent — ready to "
                   "print', while export refuses it. `verdict` unifies all "
                   "three; the score does not.",
        },
        "pitfalls": [
            "Thin or serif fonts fail min_detail: a hairline does not get "
            "thicker as you scale the text. Use weight 600+ or a sans.",
            "Text below ~2.5mm triggers text_too_small on a 0.4mm nozzle.",
            "Every feature's `material` must match a material `id` you "
            "declared, or validation rejects the document.",
            "Emboss height below one layer height (0.2mm) will not print.",
            "The back face prints against the bed and must stay FLAT. Emboss "
            "there is rejected and the feature produces no geometry at all — "
            "use deboss or cut to carve it, or flush to inlay it in another "
            "colour. This is the most common way to end up with a blank face.",
            "A pocket needs body under it: thickness minus depth minus ceiling "
            "must leave at least min_wall (0.8mm at a 0.4mm nozzle). An NFC "
            "tag pocket 0.9mm deep therefore needs a card of about 1.8mm.",
        ],
    }


@server.tool(
    description="Known-good documents to start from, each with its compile "
                "verdict. Editing one that already prints is far more reliable "
                "than composing a layout from nothing.")
def cardforge_examples(include_document: bool = False) -> Dict[str, Any]:
    """Every shipped example, compiled so the caller knows it actually works."""
    out: List[Dict[str, Any]] = []
    roots = [PROJECT_ROOT / "examples", PROJECT_ROOT / "examples" / "prototypes"]

    for root in roots:
        if not root.is_dir():
            continue
        for f in sorted(root.glob("*.cardforge.json")):
            rel = f.relative_to(PROJECT_ROOT).as_posix()
            entry: Dict[str, Any] = {"path": rel}
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                doc = load_document(raw)
                scene, trace, issues = compile_scene(doc, asset_root=PROJECT_ROOT)
                report = analyze(doc, scene, trace)
                v = verdict(issues, report, trace)
                entry.update({
                    "name": doc.meta.name,
                    "description": doc.meta.description,
                    "outline": {"width": doc.object.outline.width,
                                "height": doc.object.outline.height,
                                "thickness": doc.object.thickness},
                    "materials": [m.name for m in doc.materials],
                    "featureTypes": sorted({r.type for r in trace.records}),
                    "ready": v["ready"],
                    "score": report.score,
                })
                if include_document:
                    entry["document"] = doc.to_dict()
            except Exception as e:  # a broken example must not hide the rest
                entry.update({"ready": False, "error": str(e)})
            out.append(entry)

    return {"count": len(out), "examples": out,
            "hint": "Load one with cardforge_compile(path=...) or "
                    "cardforge_migrate(path=..., save_to=...) to get an "
                    "editable v2 copy."}


@server.tool(
    description="The raw v2 JSON Schema. section='features' returns just the "
                "per-type feature branches (smaller); 'full' returns everything.")
def cardforge_schema(section: str = "features") -> Dict[str, Any]:
    from cardforge.document.schema_v2 import load_schema

    schema = load_schema()
    if section == "features":
        branches = schema["$defs"]["feature"]["allOf"][1]["oneOf"]
        return {"section": "features",
                "base": schema["$defs"]["featureBase"],
                "types": {b["properties"]["type"]["const"]: b for b in branches}}
    if section == "full":
        return {"section": "full", "schema": schema}
    return {"error": f"Unknown section '{section}' — use 'features' or 'full'"}


@server.tool(
    description="Font families the kernel can actually render on this machine. "
                "Naming a family that is not here makes text fall back silently, "
                "so check before authoring.")
def cardforge_fonts(contains: Optional[str] = None,
                    limit: int = 60) -> Dict[str, Any]:
    from cardforge.kernel.fonts import list_families

    fonts = list_families()
    if contains:
        needle = contains.lower()
        fonts = [f for f in fonts if needle in f["family"].lower()]
    return {"total": len(fonts), "returned": min(len(fonts), limit),
            "fonts": fonts[:limit]}


@server.tool(
    description="Compile a document and get the manufacturing verdict: score, "
                "issues with fix suggestions, and where each feature landed in "
                "mm. Returns no geometry — pass save_3mf_to to write the 3MF.")
def cardforge_compile(document: Optional[Dict[str, Any]] = None,
                      path: Optional[str] = None,
                      save_3mf_to: Optional[str] = None) -> Dict[str, Any]:
    doc, err = _load(document, path)
    if err:
        return err

    try:
        scene, trace, issues = compile_scene(doc, asset_root=PROJECT_ROOT)
        report = analyze(doc, scene, trace)
    except Exception as e:
        return {"ok": False, "stage": "compile", "error": str(e)}

    out: Dict[str, Any] = {
        "ok": True,
        "name": doc.meta.name,
        # First, because it is the only field that answers "am I done?".
        # `manufacturing.score` below is one channel of three and will happily
        # read 100 on a document that export refuses.
        "verdict": verdict(issues, report, trace),
        "manufacturing": report_json(report),
        "constraints": issues_json(issues),
        "warnings": trace.warnings,
        "skippedFeatures": trace.skipped,
        "featureBounds": feature_bounds_json(trace),
        "outline": {"width": doc.object.outline.width,
                    "height": doc.object.outline.height,
                    "thickness": doc.object.thickness},
        "materials": materials_json(scene, doc),
        "parts": parts_json(scene, doc),
        "stats": {"compileMs": round(trace.elapsed_ms, 1),
                  "featureCount": len(trace.records)},
    }

    if save_3mf_to:
        from cardforge.export.threemf import scene_to_3mf

        p = Path(save_3mf_to)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        data = scene_to_3mf(scene, doc.materials, title=doc.meta.name)
        p.write_bytes(data)
        out["saved3mf"] = {"path": str(p), "bytes": len(data)}

    return out


@server.tool(
    description="Write the full manufacturing package to disk: 3MF, one STL "
                "per material, and the manufacturing report. Refuses a document "
                "whose verdict is not ready unless ignore_errors is set.")
def cardforge_export(document: Optional[Dict[str, Any]] = None,
                     path: Optional[str] = None,
                     out_dir: str = "exports",
                     formats: Optional[List[str]] = None,
                     ignore_errors: bool = False) -> Dict[str, Any]:
    from cardforge.export.stl import scene_to_stls
    from cardforge.export.threemf import scene_to_3mf

    doc, err = _load(document, path)
    if err:
        return err

    formats = formats or ["3mf", "stl"]

    try:
        scene, trace, issues = compile_scene(doc, asset_root=PROJECT_ROOT)
        report = analyze(doc, scene, trace)
    except Exception as e:
        return {"ok": False, "stage": "compile", "error": str(e)}

    # Gate on the verdict, not on the error counts: a skipped feature raises
    # no constraint and no manufacturing error, yet the model is missing it.
    v = verdict(issues, report, trace)
    if not v["ready"] and not ignore_errors:
        return {
            "ok": False, "stage": "blocked",
            "error": "Document is not ready — fix verdict.blockers, or re-call "
                     "with ignore_errors=true to export anyway",
            "verdict": v,
        }

    root = Path(out_dir)
    if not root.is_absolute():
        root = PROJECT_ROOT / root

    try:
        threemf = (scene_to_3mf(scene, doc.materials, title=doc.meta.name)
                   if "3mf" in formats else None)
        stls = scene_to_stls(scene, doc.materials) if "stl" in formats else None
        written = write_package(root, doc, threemf, stls, report)
    except Exception as e:
        return {"ok": False, "stage": "write", "error": str(e)}

    return {"ok": True, "outDir": str(root / safe_id(doc.meta.id)),
            "files": [{"path": str(f), "bytes": f.stat().st_size}
                      for f in written],
            "verdict": v,
            "manufacturing": report_json(report),
            "exportedWithErrors": not v["ready"]}


@server.tool(
    description="Normalize a legacy v1 document (or verify a v2 one) into a "
                "validated v2 document. Use this to modernize the files in "
                "examples/ before editing them.")
def cardforge_migrate(document: Optional[Dict[str, Any]] = None,
                      path: Optional[str] = None,
                      save_to: Optional[str] = None) -> Dict[str, Any]:
    from cardforge.document.schema_v2 import DocumentValidationError, validate_v2

    try:
        raw = _resolve_input(document, path)
    except (ValueError, json.JSONDecodeError) as e:
        return {"ok": False, "stage": "input", "error": str(e)}

    try:
        raw, migrated = normalize_document(raw)
    except ValueError as e:
        return {"ok": False, "stage": "detect", "error": str(e)}

    try:
        validate_v2(raw)
    except DocumentValidationError as e:
        return {"ok": False, "stage": "validation",
                "error": "Document invalid after migration",
                "problems": e.errors[:20]}

    out: Dict[str, Any] = {"ok": True, "migrated": migrated, "document": raw}
    if save_to:
        p = Path(save_to)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        out["savedTo"] = str(p)
    return out


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
