"""CardForge Core API v2 — in-process compile/export over the geometry kernel.

POST /api/compile  {document}            → 3MF (base64) + constraints + stats.
                   The returned bytes ARE the export — the Studio preview and
                   the saved file are byte-identical by construction.
POST /api/export   {document, formats}   → zip with 3MF + per-material STLs
                   + manufacturing report.
GET  /api/health
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

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


def _load_document(doc_data: dict):
    """Raw dict (v1 or v2) → resolved DocumentV2. Raises on invalid input."""
    from cardforge.document.migrate import detect_version, migrate_v1_to_v2
    from cardforge.document.schema_v2 import DocumentV2
    from cardforge.document.variables import resolve_variables

    version = detect_version(doc_data)
    if version == "1":
        doc_data = migrate_v1_to_v2(doc_data)
    elif version != "2":
        raise ValueError("Not a CardForge document (v1 or v2)")
    return DocumentV2.from_dict(resolve_variables(doc_data))


def _compile(doc):
    from cardforge.kernel.compile import compile_document
    from cardforge.kernel.constraints import check_constraints

    scene, trace = compile_document(doc, asset_root=PROJECT_ROOT)
    issues = check_constraints(doc, trace)
    return scene, trace, issues


def _issues_json(issues):
    return [
        {"severity": i.severity.value, "code": i.code, "message": i.message,
         "featureId": i.feature_id, "faceId": i.face_id}
        for i in issues
    ]


def _report_json(report):
    return {
        "score": report.score,
        "scoreLabel": report.score_label,
        "isManufacturable": report.is_manufacturable,
        "errorCount": len(report.errors),
        "warningCount": len(report.warnings),
        "issues": [
            {"code": i.code.value, "severity": i.severity.value,
             "message": i.message, "featureId": i.node_id,
             "suggestion": i.suggestion}
            for i in report.issues
        ],
    }


@app.get("/api/health")
def health():
    return {"ok": True, "version": "2.0.0",
            "timestamp": datetime.now().isoformat()}


@app.post("/api/compile")
def api_compile(body: dict):
    """Compile a document for live preview. Fast path — no files touched."""
    from cardforge.document.schema_v2 import DocumentValidationError
    from cardforge.export.threemf import scene_to_3mf
    from cardforge.manufacturing.analyzer import ManufacturingAnalyzer, profile_by_name

    try:
        doc = _load_document(body.get("document") or {})
    except DocumentValidationError as e:
        return _error(422, "Document invalid", details=e.errors[:20])
    except (ValueError, KeyError, TypeError) as e:
        return _error(400, str(e))

    try:
        scene, trace, issues = _compile(doc)
        threemf = scene_to_3mf(scene, doc.materials, title=doc.meta.name)
        profile = profile_by_name(body.get("profile")
                                  or doc.manufacturing.profile)
        report = ManufacturingAnalyzer(profile).analyze(doc, scene, trace)
    except Exception as e:  # compile errors are server-side bugs → 500
        return _error(500, f"Compile failed: {e}")

    vols = scene.non_empty()
    return {
        "ok": True,
        "model3mfBase64": base64.b64encode(threemf).decode(),
        "constraints": _issues_json(issues),
        "warnings": trace.warnings,
        "skippedFeatures": trace.skipped,
        "manufacturing": _report_json(report),
        "stats": {
            "compileMs": round(trace.elapsed_ms, 1),
            "featureCount": len(trace.records),
            "threeMfBytes": len(threemf),
        },
        "materials": [
            {"id": m.id, "name": m.name, "color": m.color, "slot": m.slot,
             "role": m.role, "present": m.id in vols,
             "volumeMm3": round(vols[m.id].volume(), 2) if m.id in vols else 0.0}
            for m in doc.materials
        ],
    }


@app.post("/api/export")
def api_export(body: dict):
    """Full export: zip with 3MF + per-material STLs + manufacturing report."""
    from cardforge.document.schema_v2 import DocumentValidationError
    from cardforge.export.stl import scene_to_stls
    from cardforge.export.threemf import scene_to_3mf
    from cardforge.kernel.types import Severity
    from cardforge.manufacturing.analyzer import ManufacturingAnalyzer, profile_by_name

    try:
        doc = _load_document(body.get("document") or {})
    except DocumentValidationError as e:
        return _error(422, "Document invalid", details=e.errors[:20])
    except (ValueError, KeyError, TypeError) as e:
        return _error(400, str(e))

    formats = body.get("formats") or ["3mf", "stl"]
    ignore_errors = bool(body.get("ignoreErrors"))

    try:
        scene, trace, issues = _compile(doc)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        profile = profile_by_name(body.get("profile") or doc.manufacturing.profile)
        report = ManufacturingAnalyzer(profile).analyze(doc, scene, trace)

        if (errors or report.has_errors) and not ignore_errors:
            return _error(
                409, "Document has blocking errors; pass ignoreErrors to override",
                constraints=_issues_json(errors),
                manufacturing=_report_json(report))

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
                        json.dumps(_report_json(report), indent=2))
    except Exception as e:
        return _error(500, f"Export failed: {e}")

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition":
                 f'attachment; filename="{doc.meta.id}_export.zip"'})
