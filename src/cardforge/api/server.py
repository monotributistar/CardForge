"""CardForge Core API v2 — in-process compile/export over the geometry kernel.

GET  /api/health
GET  /api/schema   [?section=full|features]  → the v2 JSON Schema
GET  /api/fonts                              → renderable font families
POST /api/migrate  {document}                → normalized v2 document
POST /api/compile  {document}                → 3MF (base64) + constraints + stats.
                   The returned bytes ARE the export — the Studio preview and
                   the saved file are byte-identical by construction.
POST /api/export   {document, formats}       → zip with 3MF + per-material STLs
                   + manufacturing report.

The load → compile → analyze sequence lives in `cardforge.service`, shared
with the MCP server so both front doors behave identically.
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from cardforge.service import (
    PROJECT_ROOT,
    analyze,
    compile_scene,
    feature_bounds_json,
    issues_json,
    load_document,
    materials_json,
    parts_json,
    report_json,
)

app = FastAPI(title="CardForge Core API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error(status: int, message: str, **extra):
    return JSONResponse(status_code=status,
                        content={"ok": False, "error": message, **extra})


def _load(body: dict):
    """Body → (DocumentV2, None) on success, (None, error response) otherwise."""
    from cardforge.document.schema_v2 import DocumentValidationError

    try:
        return load_document(body.get("document") or {}), None
    except DocumentValidationError as e:
        return None, _error(422, "Document invalid", details=e.errors[:20])
    except (ValueError, KeyError, TypeError) as e:
        return None, _error(400, str(e))


@app.get("/api/health")
def health():
    return {"ok": True, "version": "2.0.0",
            "timestamp": datetime.now().isoformat()}


@app.get("/api/schema")
def api_schema(section: str = "full"):
    """The v2 JSON Schema — so a client (or an agent) can discover the
    document format instead of being told it out of band.

    section=full      the whole schema
    section=features  the shared feature base plus the per-type branches
    """
    from cardforge.document.schema_v2 import load_schema

    schema = load_schema()
    if section == "features":
        branches = schema["$defs"]["feature"]["allOf"][1]["oneOf"]
        return {"ok": True, "version": "2.0", "section": "features",
                "base": schema["$defs"]["featureBase"],
                "types": {b["properties"]["type"]["const"]: b for b in branches}}
    if section != "full":
        return _error(400, f"Unknown section '{section}' (full|features)")
    return {"ok": True, "version": "2.0", "section": "full", "schema": schema}


@app.get("/api/fonts")
def api_fonts():
    """Font families the kernel can render — for the editor's font picker."""
    from cardforge.kernel.fonts import list_families

    return {"ok": True, "fonts": list_families()}


@app.post("/api/migrate")
def api_migrate(body: dict):
    """Normalize any document (v1 or v2) to validated v2 — the Studio uses
    this on Open so the editor always works on v2 natively."""
    from cardforge.document.migrate import detect_version, migrate_v1_to_v2
    from cardforge.document.schema_v2 import DocumentValidationError, validate_v2

    data = body.get("document") or {}
    version = detect_version(data)
    if version == "1":
        data = migrate_v1_to_v2(data)
    elif version != "2":
        return _error(400, "Not a CardForge document (v1 or v2)")
    try:
        validate_v2(data)
    except DocumentValidationError as e:
        return _error(422, "Document invalid after migration", details=e.errors[:20])
    return {"ok": True, "document": data, "migrated": version == "1"}


@app.post("/api/compile")
def api_compile(body: dict):
    """Compile a document for live preview. Fast path — no files touched."""
    from cardforge.export.threemf import scene_to_3mf

    doc, err = _load(body)
    if err:
        return err

    try:
        scene, trace, issues = compile_scene(doc, asset_root=PROJECT_ROOT)
        threemf = scene_to_3mf(scene, doc.materials, title=doc.meta.name)
        report = analyze(doc, scene, trace)
    except Exception as e:  # compile errors are server-side bugs → 500
        return _error(500, f"Compile failed: {e}")

    return {
        "ok": True,
        "model3mfBase64": base64.b64encode(threemf).decode(),
        "constraints": issues_json(issues),
        "warnings": trace.warnings,
        "skippedFeatures": trace.skipped,
        "manufacturing": report_json(report),
        "stats": {
            "compileMs": round(trace.elapsed_ms, 1),
            "featureCount": len(trace.records),
            "threeMfBytes": len(threemf),
        },
        "parts": parts_json(scene, doc),
        "featureBounds": feature_bounds_json(trace),
        "materials": materials_json(scene, doc),
    }


@app.post("/api/export")
def api_export(body: dict):
    """Full export: zip with 3MF + per-material STLs + manufacturing report."""
    from cardforge.export.stl import scene_to_stls
    from cardforge.export.threemf import scene_to_3mf
    from cardforge.kernel.types import Severity

    doc, err = _load(body)
    if err:
        return err

    formats = body.get("formats") or ["3mf", "stl"]
    ignore_errors = bool(body.get("ignoreErrors"))

    try:
        scene, trace, issues = compile_scene(doc, asset_root=PROJECT_ROOT)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        report = analyze(doc, scene, trace)

        if (errors or report.has_errors) and not ignore_errors:
            return _error(
                409, "Document has blocking errors; pass ignoreErrors to override",
                constraints=issues_json(errors),
                manufacturing=report_json(report))

        # Single-format 3MF: return the raw file — no zip wrapper, no report.
        if formats == ["3mf"]:
            return Response(
                content=scene_to_3mf(scene, doc.materials, title=doc.meta.name),
                media_type="model/3mf",
                headers={"Content-Disposition":
                         f'attachment; filename="{doc.meta.id}.3mf"'})

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            if "3mf" in formats:
                zf.writestr(f"{doc.meta.id}.3mf",
                            scene_to_3mf(scene, doc.materials, title=doc.meta.name))
            if "stl" in formats:
                for mid, data in scene_to_stls(scene, doc.materials).items():
                    mat = doc.material_by_id(mid)
                    slot = f"_slot{mat.slot}" if mat and mat.slot else ""
                    zf.writestr(f"stl/{mid}{slot}.stl", data)
            zf.writestr("manufacturing_report.json",
                        json.dumps(report_json(report), indent=2))
    except Exception as e:
        return _error(500, f"Export failed: {e}")

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition":
                 f'attachment; filename="{doc.meta.id}_export.zip"'})
