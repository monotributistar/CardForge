"""v2 pipeline stages — load → resolve → compile → constraints → analyze → export.

Each stage reads/writes the shared context dict and returns a StageResult.
The orchestrator (unchanged) runs them in order and stops on error.

Context keys:
    in:  document_path | document_data, exports_dir, manufacturing_profile,
         ignore_manufacturing_errors, asset_root
    out: document (DocumentV2), scene (CompiledScene), trace (CompileTrace),
         constraint_issues, manufacturing_report, threemf_bytes, stl_bytes,
         written_files
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from cardforge.pipeline.orchestrator import StageResult


def load_document_stage(ctx: Dict[str, Any]) -> StageResult:
    """Load + migrate + validate into a DocumentV2 (variables unresolved)."""
    from cardforge.document.migrate import detect_version, migrate_v1_to_v2
    from cardforge.document.schema_v2 import DocumentValidationError
    from cardforge.document.variables import resolve_variables

    try:
        if "document_data" in ctx:
            data = ctx["document_data"]
        else:
            path = Path(ctx["document_path"])
            if not path.exists():
                return StageResult.error(f"Document not found: {path}")
            data = json.loads(path.read_text())

        version = detect_version(data)
        if version == "1":
            data = migrate_v1_to_v2(data)
        elif version != "2":
            return StageResult.error("Not a CardForge document (v1 or v2)")

        resolved = resolve_variables(data)

        from cardforge.document.schema_v2 import DocumentV2
        ctx["document"] = DocumentV2.from_dict(resolved)
        ctx["document_raw"] = data  # unresolved, for re-save
        return StageResult.ok(f"Loaded document '{ctx['document'].meta.name}'"
                              + (" (migrated from v1)" if version == "1" else ""))
    except DocumentValidationError as e:
        return StageResult.error(f"Document invalid: {'; '.join(e.errors[:5])}")
    except json.JSONDecodeError as e:
        return StageResult.error(f"Invalid JSON: {e}")


def compile_stage(ctx: Dict[str, Any]) -> StageResult:
    """Document → CompiledScene + CompileTrace via the geometry kernel."""
    from cardforge.kernel.compile import compile_document

    doc = ctx["document"]
    scene, trace = compile_document(doc, asset_root=ctx.get("asset_root", "."))
    ctx["scene"] = scene
    ctx["trace"] = trace
    vols = scene.non_empty()
    msg = (f"Compiled {len(trace.records)} features → "
           f"{len(vols)} material volumes in {trace.elapsed_ms:.0f}ms")
    if trace.skipped:
        msg += f" ({len(trace.skipped)} skipped)"
    return StageResult.ok(msg)


def constraints_stage(ctx: Dict[str, Any]) -> StageResult:
    from cardforge.kernel.constraints import check_constraints
    from cardforge.kernel.types import Severity

    issues = check_constraints(ctx["document"], ctx["trace"])
    ctx["constraint_issues"] = issues
    errors = [i for i in issues if i.severity == Severity.ERROR]
    if errors and not ctx.get("ignore_constraint_errors"):
        msgs = "; ".join(f"{i.feature_id}: {i.message}" for i in errors[:3])
        return StageResult.error(f"{len(errors)} constraint error(s): {msgs}")
    return StageResult.ok(f"Constraints: {len(issues)} issue(s)")


def manufacturing_stage(ctx: Dict[str, Any]) -> StageResult:
    from cardforge.manufacturing.analyzer import (
        ManufacturingAnalyzer, profile_by_name, resolve_profile)
    from cardforge.manufacturing.formatter import format_report_console

    # An explicit profile override wins; otherwise derive from the document nozzle.
    override = ctx.get("manufacturing_profile")
    profile = profile_by_name(override) if override else resolve_profile(ctx["document"])
    analyzer = ManufacturingAnalyzer(profile)
    report = analyzer.analyze(ctx["document"], ctx["scene"], ctx["trace"])
    ctx["manufacturing_report"] = report
    ctx["manufacturing_console"] = format_report_console(report)

    if report.has_errors and not ctx.get("ignore_manufacturing_errors"):
        return StageResult.error(
            f"Manufacturing errors block export (score {report.score}/100). "
            "Pass ignore_manufacturing_errors to override.")
    return StageResult.ok(f"Manufacturing score {report.score}/100")


def export_3mf_stage(ctx: Dict[str, Any]) -> StageResult:
    from cardforge.export.threemf import scene_to_3mf

    doc = ctx["document"]
    data = scene_to_3mf(ctx["scene"], doc.materials, title=doc.meta.name)
    ctx["threemf_bytes"] = data
    return StageResult.ok(f"3MF: {len(data) / 1024:.0f} KB")


def export_stl_stage(ctx: Dict[str, Any]) -> StageResult:
    from cardforge.export.stl import scene_to_stls

    doc = ctx["document"]
    ctx["stl_bytes"] = scene_to_stls(ctx["scene"], doc.materials)
    sizes = {m: f"{len(b) / 1024:.0f}KB" for m, b in ctx["stl_bytes"].items()}
    return StageResult.ok(f"STL parts: {sizes}")


def write_outputs_stage(ctx: Dict[str, Any]) -> StageResult:
    """Persist exports to exports_dir/<doc-id>/ and write the report files.

    The stl/ subdir and root *.3mf files are wholly owned by this stage, so
    stale files from earlier runs (renamed materials, old pipeline layouts)
    are removed first — leftovers would get imported into the slicer
    alongside the fresh parts.
    """
    import shutil

    from cardforge.manufacturing.export_report import (
        export_report_json, export_report_markdown)

    doc = ctx["document"]
    out_root = Path(ctx.get("exports_dir", "exports")) / doc.meta.id
    out_root.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(out_root / "stl", ignore_errors=True)
    for stale in out_root.glob("*.3mf"):
        stale.unlink()
    written = []

    threemf = ctx.get("threemf_bytes")
    if threemf:
        p = out_root / f"{doc.meta.id}.3mf"
        p.write_bytes(threemf)
        written.append(p)

    for mid, data in (ctx.get("stl_bytes") or {}).items():
        mat = doc.material_by_id(mid)
        slot = f"_slot{mat.slot}" if mat and mat.slot else ""
        p = out_root / "stl" / f"{mid}{slot}.stl"
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(data)
        written.append(p)

    report = ctx.get("manufacturing_report")
    if report:
        reports_dir = out_root / "reports"
        reports_dir.mkdir(exist_ok=True)
        written.append(export_report_json(report, reports_dir / "manufacturing.json"))
        written.append(export_report_markdown(report, reports_dir / "manufacturing.md"))

    ctx["written_files"] = written
    listing = "\n".join(f"  - {p}" for p in written)
    return StageResult.ok(f"Wrote {len(written)} files:\n{listing}")


def build_pipeline(export_stl: bool = True):
    """The standard v2 build pipeline."""
    from cardforge.pipeline.orchestrator import Pipeline

    p = Pipeline()
    p.add_stage("load", load_document_stage)
    p.add_stage("compile", compile_stage)
    p.add_stage("constraints", constraints_stage)
    p.add_stage("manufacturing", manufacturing_stage)
    p.add_stage("export_3mf", export_3mf_stage)
    if export_stl:
        p.add_stage("export_stl", export_stl_stage)
    p.add_stage("write", write_outputs_stage)
    return p
