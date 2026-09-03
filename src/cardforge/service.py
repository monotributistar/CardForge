"""Shared compile service — the one path from a raw document to geometry.

Both front doors go through here: the HTTP API (`cardforge.api.server`) that
the Studio talks to, and the MCP server (`cardforge.mcp_server`) that an agent
talks to. Keeping the load/compile/analyze sequence in a single place is what
guarantees a model and a human see the same constraints, the same score and
the same geometry rather than two implementations that drift apart.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_document(doc_data: Dict[str, Any]):
    """Raw dict (v1 or v2) → resolved, validated DocumentV2.

    Raises ValueError for a non-CardForge dict and DocumentValidationError
    when the document does not satisfy the v2 schema.
    """
    from cardforge.document.migrate import detect_version, migrate_v1_to_v2
    from cardforge.document.schema_v2 import DocumentV2
    from cardforge.document.variables import resolve_variables

    version = detect_version(doc_data)
    if version == "1":
        doc_data = migrate_v1_to_v2(doc_data)
    elif version != "2":
        raise ValueError("Not a CardForge document (v1 or v2)")
    return DocumentV2.from_dict(resolve_variables(doc_data))


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
