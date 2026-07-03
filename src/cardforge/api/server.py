"""CardForge Core API server — FastAPI HTTP interface to the Core Compiler."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uuid
import json
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

app = FastAPI(title="CardForge Core API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage ──────────────────────────────────────────────────────────
EXPORTS_DIR = Path("exports/api")
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
_jobs: dict = {}


@app.get("/api/health")
def health():
    return {"ok": True, "version": "0.1.0", "timestamp": datetime.now().isoformat()}


@app.post("/api/preview")
def api_preview(body: dict):
    """Generate SVG preview + manufacturing report from a document."""
    try:
        doc_data = body.get("document", {})
        profile_name = body.get("profile", "fdm-standard")

        # Resolve document and adapt to legacy config
        from cardforge.document.model import CardForgeDocument
        from cardforge.document.adapter import resolve_document_variables, adapt_to_legacy_config
        from cardforge.domain.factory import create_card_from_config
        from cardforge.geometry_ir.builder import GeometryBuilder
        from cardforge.geometry_ir.svg_visitor import SVGVisitor
        from cardforge.manufacturing.profiles import ManufacturingProfile
        from cardforge.manufacturing.analyzer import ManufacturingAnalyzer

        doc = CardForgeDocument.from_dict(doc_data)
        doc = resolve_document_variables(doc)
        config = adapt_to_legacy_config(doc)
        card = create_card_from_config(config)
        builder = GeometryBuilder()
        geometry_doc = builder.build(card)

        # SVG previews
        front_visitor = SVGVisitor(face_id="front")
        back_visitor = SVGVisitor(face_id="back")
        front_svg = front_visitor.render(geometry_doc)
        back_svg = back_visitor.render(geometry_doc)

        # Manufacturing analysis
        profile = ManufacturingProfile.fdm_standard()
        analyzer = ManufacturingAnalyzer(profile)
        report = analyzer.analyze(geometry_doc)

        return {
            "ok": True,
            "preview": {"frontSvg": front_svg, "backSvg": back_svg},
            "manufacturing": {
                "score": report.score,
                "scoreLabel": report.score_label,
                "isManufacturable": report.is_manufacturable,
                "errorCount": len(report.errors),
                "warningCount": len(report.warnings),
                "warnings": [{"code": i.code.value, "message": i.message, "suggestion": i.suggestion} for i in report.warnings],
                "errors": [{"code": i.code.value, "message": i.message} for i in report.errors],
                "suggestions": report.suggestions,
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/manufacture")
def api_manufacture(body: dict):
    """Full manufacture: generate STL + parts + reports + manifest."""
    try:
        doc_data = body.get("document", {})
        options = body.get("options", {})

        job_id = str(uuid.uuid4())[:8]
        job_dir = EXPORTS_DIR / job_id
        job_dir.mkdir(parents=True)

        _jobs[job_id] = {"status": "running", "progress": 0, "steps": []}

        # Save document
        doc_path = job_dir / "document.cardforge.json"
        doc_path.write_text(json.dumps(doc_data))

        # Run Core CLI
        import subprocess, sys
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        cli = project_root / "scripts" / "core_cli.py"

        _jobs[job_id]["steps"].append({"name": "preview", "status": "running"})
        result = subprocess.run(
            [sys.executable, str(cli), "preview", str(doc_path)],
            capture_output=True, text=True, timeout=120, cwd=str(project_root),
        )
        _jobs[job_id]["steps"][-1]["status"] = "done" if result.returncode == 0 else "failed"

        if result.returncode != 0:
            _jobs[job_id]["status"] = "failed"
            detail = (result.stderr or result.stdout or "")[:1000]
            _jobs[job_id]["error"] = detail
            return {
                "ok": False, "error": "Preview failed",
                "returncode": result.returncode,
                "python": sys.executable,
                "stderr": result.stderr[:1000],
                "stdout": result.stdout[:1000],
            }

        try:
            preview_result = json.loads(result.stdout)
        except json.JSONDecodeError:
            preview_result = {"manufacturing": {"score": 0, "scoreLabel": "?"}}

        # Run legacy build for STL generation
        _jobs[job_id]["steps"].append({"name": "stl", "status": "running"})
        build_script = project_root / "scripts" / "build.py"
        do_stl = options.get("singleStl", True)
        do_parts = options.get("parts", True)

        # Use a temp file for the build script input
        legacy_config = _adapt_doc_to_legacy_config(doc_data)
        config_path = job_dir / "_config.json"
        config_path.write_text(json.dumps(legacy_config))

        cmd = [sys.executable, str(build_script), str(config_path), "--clean"]
        if do_stl:
            cmd.append("--stl")
        if do_parts:
            cmd.append("--parts")

        build_result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, cwd=str(project_root),
        )
        _jobs[job_id]["steps"][-1]["status"] = "done" if build_result.returncode == 0 else "failed"

        if build_result.returncode != 0:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = build_result.stderr[:500]
            return {"ok": False, "error": "Build failed", "stderr": build_result.stderr[:500]}

        # Find generated exports
        mfg = preview_result.get("manufacturing", {})
        project_name = legacy_config.get("project", {}).get("name", job_id)
        safe_name = _sanitize(project_name)
        export_root = project_root / "exports" / safe_name

        # Copy files to job directory
        stl_dir = job_dir / "stl"
        stl_dir.mkdir(exist_ok=True)
        parts_dir = job_dir / "stl" / "parts"
        parts_dir.mkdir(exist_ok=True)

        files = []
        # Single STL
        single_stl = export_root / "stl" / "card_single.stl"
        if single_stl.exists():
            shutil.copy2(single_stl, stl_dir / "card_single.stl")
            files.append({"name": "stl/card_single.stl", "type": "stl", "url": f"/api/files/{job_id}/stl/card_single.stl"})

        # Parts
        parts_src = export_root / "stl" / "parts"
        stl_parts = []
        if parts_src.exists():
            for f in sorted(parts_src.glob("*.stl")):
                shutil.copy2(f, parts_dir / f.name)
                files.append({"name": f"stl/parts/{f.name}", "type": "stl_part", "url": f"/api/files/{job_id}/stl/parts/{f.name}"})
                stl_parts.append(f)

        # Generate 3MF from STL parts
        if stl_parts:
            from cardforge.api.generate_3mf import generate_3mf
            colors = {"base": "#3a3a3a", "pla": "#3a3a3a", "text": "#e0e0e0", "accent": "#d4af37"}
            part_data = []
            for f in stl_parts:
                mat = "base"
                name = f.stem
                if "text" in name.lower() or "white" in name.lower():
                    mat = "text"
                elif "accent" in name.lower() or "gold" in name.lower():
                    mat = "accent"
                part_data.append({
                    "name": name,
                    "stl_path": str(f),
                    "color_hex": colors.get(mat, "#808080"),
                    "material_name": mat.upper(),
                })
            try:
                mf3_path = generate_3mf(part_data, job_dir / "stl")
                files.append({"name": "card.3mf", "type": "3mf", "url": f"/api/files/{job_id}/stl/card.3mf"})
            except Exception as e:
                # 3MF generation is best-effort, don't fail the whole build
                pass

        # Preview SVGs
        preview_dir = job_dir / "preview"
        preview_dir.mkdir(exist_ok=True)
        preview_src = export_root / "preview"
        if preview_src.exists():
            for f in preview_src.glob("*.svg"):
                shutil.copy2(f, preview_dir / f.name)
                files.append({"name": f"preview/{f.name}", "type": "preview", "url": f"/api/files/{job_id}/preview/{f.name}"})

        # Reports
        reports_dir = job_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        reports_src = export_root / "reports"
        if reports_src.exists():
            for f in reports_src.glob("*"):
                shutil.copy2(f, reports_dir / f.name)
                files.append({"name": f"reports/{f.name}", "type": "report", "url": f"/api/files/{job_id}/reports/{f.name}"})

        manifest = {
            "document": project_name,
            "version": "0.1.0",
            "timestamp": datetime.now().isoformat(),
            "profile": "fdm-standard",
            "score": mfg.get("score", 0),
            "scoreLabel": mfg.get("scoreLabel", "?"),
            "manufacturable": mfg.get("isManufacturable", True),
            "files": files,
        }

        _jobs[job_id] = {"status": "completed", "progress": 100, "steps": _jobs[job_id]["steps"], "manifest": manifest}
        return {"ok": True, "jobId": job_id, "status": "completed", "package": {"manifest": manifest, "files": files}}
    except Exception as e:
        job_id = job_id if 'job_id' in dir() else "unknown"
        _jobs[job_id] = {"status": "failed", "error": str(e)}
        return {"ok": False, "error": str(e)}


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return {"ok": False, "error": "Job not found"}
    return {"ok": True, "jobId": job_id, **job}


@app.get("/api/files/{job_id}/{path:path}")
def api_file(job_id: str, path: str):
    file_path = EXPORTS_DIR / job_id / path
    if not file_path.exists():
        return {"ok": False, "error": "File not found"}
    return FileResponse(file_path, filename=Path(path).name)


# ── Helpers ──────────────────────────────────────────────────────────────

def _sanitize(name: str) -> str:
    import re
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name).strip('_')


def _adapt_doc_to_legacy_config(doc_data: dict) -> dict:
    """Convert document format to legacy config using the real adapter."""
    from cardforge.document.model import CardForgeDocument
    from cardforge.document.adapter import resolve_document_variables, adapt_to_legacy_config

    doc = CardForgeDocument.from_dict(doc_data)
    doc = resolve_document_variables(doc)
    return adapt_to_legacy_config(doc)
