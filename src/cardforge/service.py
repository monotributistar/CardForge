"""Shared compile service — the one path from a raw document to geometry.

Every front door goes through here: the CLI pipeline, the HTTP API
(`cardforge.api.server`) that the Studio talks to, and the MCP server
(`cardforge.mcp_server`) that an agent talks to. Keeping load / compile /
analyze / verdict / write in a single place is what guarantees a model and a
human see the same constraints, the same score, the same geometry and the same
files on disk rather than three implementations that drift apart.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cardforge.paths import project_root

PROJECT_ROOT = project_root()


# ── Loading ──────────────────────────────────────────────────────────

def normalize_document(doc_data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Raw dict (v1 or v2) → (v2 dict, migrated?).

    Raises ValueError for a dict that is not a CardForge document, or for a
    v1 document the migrator cannot make sense of.
    """
    from cardforge.document.migrate import detect_version, migrate_v1_to_v2

    version = detect_version(doc_data)
    if version == "2":
        return doc_data, False
    if version != "1":
        raise ValueError("Not a CardForge document (v1 or v2)")
    try:
        return migrate_v1_to_v2(doc_data), True
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise ValueError(f"Cannot migrate v1 document: {e}") from e


def load_document(doc_data: Dict[str, Any]):
    """Raw dict (v1 or v2) → resolved, validated DocumentV2.

    Raises ValueError for a non-CardForge dict or an unresolvable `{{var}}`
    reference, and DocumentValidationError when the document does not
    satisfy the v2 schema.
    """
    from cardforge.document.schema_v2 import DocumentV2
    from cardforge.document.variables import resolve_variables

    data, _ = normalize_document(doc_data)
    return DocumentV2.from_dict(resolve_variables(data))


def compile_scene(doc, asset_root: Path | str = PROJECT_ROOT):
    """DocumentV2 → (scene, trace, constraint issues)."""
    from cardforge.kernel.compile import compile_document
    from cardforge.kernel.constraints import check_constraints

    scene, trace = compile_document(doc, asset_root=asset_root)
    return scene, trace, check_constraints(doc, trace)


def analyze(doc, scene, trace):
    """Run the manufacturing analyzer under the document's own profile."""
    from cardforge.manufacturing.analyzer import ManufacturingAnalyzer, resolve_profile

    return ManufacturingAnalyzer(resolve_profile(doc)).analyze(doc, scene, trace)


# ── The verdict ──────────────────────────────────────────────────────

def _feature_of_warning(warning: str, known_ids) -> Optional[str]:
    """Compiler warnings are `"{face}/{feature-id}: {message}"`. Feature ids
    are free strings and may themselves contain `:` or `/`, so match against
    the ids we know rather than splitting on punctuation."""
    _, sep, rest = warning.partition("/")
    if not sep:
        return None
    for fid in sorted(known_ids, key=len, reverse=True):
        if rest.startswith(f"{fid}: "):
            return fid
    return None


def verdict(issues, report, trace) -> Dict[str, Any]:
    """One answer to "is this done?", drawn from all three feedback channels.

    A compile reports through three of them — kernel constraints, the
    manufacturing analyzer, and the compiler's own trace — and none is a
    superset of the others. The manufacturing score in particular only sees
    its own channel, so a document whose feature silently produced no
    geometry still scores 100 and calls itself "ready to print".

    `ready` is the boolean every export gate uses. A skipped feature always
    blocks: asking for something and not getting it is a failure even when
    every rule the analyzer knows is satisfied.
    """
    from cardforge.kernel.types import Severity as KernelSeverity
    from cardforge.manufacturing.issues import Severity as MfgSeverity

    blockers: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    def add(entry, blocking):
        (blockers if blocking else warnings).append(entry)

    # Kernel constraints — geometry the compiler cannot honour as authored.
    for i in issues:
        add({"source": "constraint", "code": i.code, "message": i.message,
             "featureId": i.feature_id, "faceId": i.face_id},
            i.severity == KernelSeverity.ERROR)

    # Manufacturing analyzer — will it survive the printer.
    for i in report.issues:
        add({"source": "manufacturing", "code": i.code.value,
             "message": i.message, "featureId": i.node_id,
             "suggestion": i.suggestion},
            i.severity in (MfgSeverity.ERROR, MfgSeverity.FATAL))

    # A skipped feature is the quietest failure of all: the agent asked for
    # something and the model simply does not contain it. Always blocking.
    for fid in trace.skipped:
        add({"source": "compiler", "code": "feature-skipped", "featureId": fid,
             "message": f"Feature '{fid}' produced no geometry and is absent "
                        f"from the model — it was asked for and is not there",
             "suggestion": "Check the compiler note for this feature id in "
                           "`warnings`, then fix or remove the feature."},
            True)

    # Everything else the compiler said out loud while building.
    skipped = set(trace.skipped)
    known = skipped | {r.feature_id for r in trace.records}
    for w in trace.warnings:
        fid = _feature_of_warning(w, known)
        if fid in skipped:
            continue  # already reported as a blocker above
        add({"source": "compiler", "code": "compiler-note", "message": w,
             "featureId": fid}, False)

    ready = not blockers
    if ready:
        summary = (f"Ready. {len(warnings)} warning(s), "
                   f"manufacturing score {report.score}/100.")
    else:
        summary = (f"Not ready — {len(blockers)} blocker(s). "
                   f"Fix these before exporting: "
                   + "; ".join(b["code"] for b in blockers[:4]))

    return {"ready": ready, "summary": summary,
            "blockers": blockers, "warnings": warnings}


# ── Writing the package ──────────────────────────────────────────────

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_id(meta_id: str) -> str:
    """A document id as a single path segment.

    The schema only asks for a non-empty string, so `meta.id` may carry `/`,
    `..` or a drive letter. Files are named after it, so it must never be
    able to choose a directory: anything but `[A-Za-z0-9._-]` becomes `-`,
    and an id that is nothing but dots or separators falls back to `document`.
    """
    slug = _UNSAFE.sub("-", meta_id).strip("-.")
    return slug or "document"


def stl_filename(doc, material_id: str) -> str:
    """`<material>_slot<n>.stl` — the name every writer (zip, disk) agrees on."""
    mat = doc.material_by_id(material_id)
    slot = f"_slot{mat.slot}" if mat and mat.slot else ""
    return f"{material_id}{slot}.stl"


def write_package(out_root: Path, doc, threemf: Optional[bytes],
                  stls: Optional[Dict[str, bytes]], report) -> List[Path]:
    """Persist a manufacturing package to `out_root/<doc-id>/`.

    Layout (owned wholly by this function, so stale files from earlier runs —
    renamed materials, old pipeline layouts — are removed first; leftovers
    would get imported into the slicer alongside the fresh parts):

        <id>.3mf
        stl/<material>_slot<n>.stl
        reports/manufacturing.json
        reports/manufacturing.md

    Returns the files written, in order.
    """
    from cardforge.manufacturing.export_report import (
        export_report_json, export_report_markdown)

    target = Path(out_root) / safe_id(doc.meta.id)
    target.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(target / "stl", ignore_errors=True)
    for stale in target.glob("*.3mf"):
        stale.unlink()

    written: List[Path] = []
    if threemf:
        p = target / f"{safe_id(doc.meta.id)}.3mf"
        p.write_bytes(threemf)
        written.append(p)

    for mid, data in (stls or {}).items():
        p = target / "stl" / stl_filename(doc, mid)
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(data)
        written.append(p)

    if report is not None:
        reports_dir = target / "reports"
        reports_dir.mkdir(exist_ok=True)
        written.append(export_report_json(report, reports_dir / "manufacturing.json"))
        written.append(export_report_markdown(report, reports_dir / "manufacturing.md"))

    return written


# ── JSON projections ─────────────────────────────────────────────────

def issues_json(issues) -> List[Dict[str, Any]]:
    return [
        {"severity": i.severity.value, "code": i.code, "message": i.message,
         "featureId": i.feature_id, "faceId": i.face_id}
        for i in issues
    ]


def report_json(report) -> Dict[str, Any]:
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


def feature_bounds_json(trace) -> List[Dict[str, Any]]:
    """Where each feature actually landed, in DOCUMENT space (top-left
    origin, y down, mm) — the same frame the document is authored in.

    This is what makes a layout checkable without rendering: a caller can
    verify margins and overlaps by arithmetic on the numbers it gets back.
    """
    return [
        {"featureId": r.feature_id, "faceId": r.face_id, "type": r.type,
         "x": round(r.bounds.x, 2), "y": round(r.bounds.y, 2),
         "width": round(r.bounds.width, 2), "height": round(r.bounds.height, 2),
         "areaMm2": round(r.area, 2),
         "reliefMode": r.relief_mode, "reliefMm": round(r.relief_value, 3)}
        for r in trace.records
    ]


def parts_json(scene, doc) -> List[Dict[str, Any]]:
    """Per-part manifest for the 3D viewer: maps every 3MF mesh (by its
    object name) back to the feature it came from, with mm dimensions."""
    from cardforge.export.threemf import normalized_parts, part_label

    feature_ids = {f.id for _, f in doc.all_features()}

    def feature_of(part_id: str):
        if part_id == "base":
            return None
        pid = part_id.split(":", 1)[0]
        for suffix in ("-floor", "-pad"):
            if pid.endswith(suffix) and pid[:-len(suffix)] in feature_ids:
                pid = pid[:-len(suffix)]
        return pid if pid in feature_ids else None

    out = []
    for p in normalized_parts(scene):
        mat = doc.material_by_id(p.material)
        bb = p.solid.bounding_box()
        out.append({
            "id": p.id,
            "label": part_label(p, mat),
            "featureId": feature_of(p.id),
            "material": p.material,
            "slot": mat.slot if mat else None,
            "sizeMm": [round(bb[3] - bb[0], 2), round(bb[4] - bb[1], 2),
                       round(bb[5] - bb[2], 3)],
            "zMm": [round(bb[2], 3), round(bb[5], 3)],
        })
    return out


def materials_json(scene, doc) -> List[Dict[str, Any]]:
    vols = scene.non_empty()
    return [
        {"id": m.id, "name": m.name, "color": m.color, "slot": m.slot,
         "role": m.role, "present": m.id in vols,
         "volumeMm3": round(vols[m.id].volume(), 2) if m.id in vols else 0.0}
        for m in doc.materials
    ]
