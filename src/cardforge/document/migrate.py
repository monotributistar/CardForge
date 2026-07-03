"""v1 → v2 document migration.

Pure dict→dict transform (no models involved) so it is trivially testable and
usable from the loader, the API, and the Studio "open legacy file" path.

v1 layout: {document, manufacturing, variables, assets?, objects[{width,height,
thickness,cornerRadius,theme,faces}], exports}
v2 layout: see document/schema_v2.py.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

# Color names used by v1 themes (mirror of the deleted domain/factory.py map)
_COLOR_NAME_TO_HEX = {
    "black": "#1a1a1a",
    "white": "#ffffff",
    "gold": "#d4af37",
    "silver": "#c0c0c0",
    "gray": "#808080",
    "grey": "#808080",
    "red": "#cc3333",
    "blue": "#3366cc",
    "green": "#33aa55",
}

_FONT_STYLE_TO_WEIGHT = {"bold": 700, "normal": 400, "light": 300, "medium": 500}

# v1 TS-side QR field keys, kept verbatim in v2 fields{}
_QR_FIELD_KEYS = (
    "url", "text",
    "vcard_name", "vcard_title", "vcard_phone", "vcard_email", "vcard_website",
    "wifi_ssid", "wifi_password", "wifi_encryption",
    "email_address", "email_subject", "email_body",
)


def detect_version(data: Dict[str, Any]) -> str:
    """Return '2', '1', or 'unknown' for a raw document dict."""
    if data.get("cardforge") == "2.0":
        return "2"
    if "objects" in data and isinstance(data.get("document"), dict):
        return "1"
    return "unknown"


def migrate_v1_to_v2(v1: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a v1 document dict into a v2 document dict.

    Faithful, not corrective: geometry/placement semantics are preserved
    (top-left-origin mm positions, zIndex ordering, relief modes). Only
    representation changes.
    """
    v1 = copy.deepcopy(v1)
    doc_meta = v1.get("document", {})
    obj = (v1.get("objects") or [{}])[0]
    theme = obj.get("theme", {}) or {}

    materials = _materials_from_theme(theme)

    mf = v1.get("manufacturing", {}) or {}
    out: Dict[str, Any] = {
        "cardforge": "2.0",
        "meta": {
            "id": doc_meta.get("id", "untitled"),
            "name": doc_meta.get("name", "Untitled"),
        },
        "object": {
            "outline": {
                "type": "rounded-rect",
                "width": float(obj.get("width", 85)),
                "height": float(obj.get("height", 54)),
                "radius": float(obj.get("cornerRadius", 4)),
            },
            "thickness": float(obj.get("thickness", 1.8)),
        },
        "materials": materials,
        "variables": {k: str(v) for k, v in (v1.get("variables") or {}).items()},
        "assets": dict(v1.get("assets") or {}),
        "manufacturing": {
            "process": mf.get("process", "fdm"),
            "profile": mf.get("profile", "fdm-standard"),
            "nozzle": float(mf.get("nozzle", 0.4)),
            "layerHeight": float(mf.get("layerHeight", 0.2)),
        },
        "faces": {},
    }
    if doc_meta.get("description"):
        out["meta"]["description"] = doc_meta["description"]

    known_ids = {m["id"] for m in materials}
    for face_id in ("front", "back"):
        face = (obj.get("faces") or {}).get(face_id)
        if face is None:
            continue
        features = []
        for feat in face.get("features", []):
            migrated = _migrate_feature(feat, known_ids)
            if migrated is None:
                continue
            # The back face prints against the bed and must stay flat: v1
            # authored back-face emboss (never actually printable) becomes a
            # flush inlay, preserving the "coloured design on the back" intent.
            if face_id == "back" and migrated["relief"].get("mode") == "emboss":
                migrated["relief"] = {
                    "mode": "flush",
                    "depth": migrated["relief"].get("height", 0.3),
                }
            features.append(migrated)
        out["faces"][face_id] = {"features": features}

    return out


# ── Materials ──────────────────────────────────────────────────────────────

def _to_hex(color: Optional[str], fallback: str) -> str:
    if not color:
        return fallback
    c = color.strip().lower()
    if c.startswith("#") and len(c) == 7:
        return c
    return _COLOR_NAME_TO_HEX.get(c, fallback)


def _materials_from_theme(theme: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"id": "base", "name": "Base", "role": "base", "slot": 1,
         "color": _to_hex(theme.get("baseColor"), "#1a1a1a")},
        {"id": "text", "name": "Text", "role": "text", "slot": 2,
         "color": _to_hex(theme.get("textColor"), "#ffffff")},
        {"id": "accent", "name": "Accent", "role": "accent", "slot": 3,
         "color": _to_hex(theme.get("accentColor"), "#d4af37")},
    ]


# ── Features ───────────────────────────────────────────────────────────────

def _migrate_feature(f: Dict[str, Any], known_materials: set) -> Optional[Dict[str, Any]]:
    ftype = f.get("type", "")
    base = _feature_base(f, known_materials)

    if ftype == "text-block":
        base.update({
            "type": "text-block",
            "lines": [str(line) for line in f.get("lines", [])] or [""],
            "font": _font(f),
        })
        if f.get("align") and f["align"] != "left":
            base["align"] = f["align"]
        if f.get("lineHeight"):
            base["lineHeight"] = float(f["lineHeight"])
        return base

    if ftype == "qr":
        qr_type, fields = _qr_fields(f)
        size = f.get("size", 24)
        base.update({
            "type": "qr",
            "qrType": qr_type,
            "fields": fields,
            "size": float(size if isinstance(size, (int, float)) else size.get("width", 24)),
        })
        return base

    if ftype == "pattern":
        ptype = f.get("patternType", "text-repeat")
        if ptype == "text-repeat":
            base.update({
                "type": "text-pattern",
                "text": str(f.get("text", "")) or "•",
                "font": {"family": f.get("font", "sans-serif"),
                         "size": float(f.get("fontSize", 4.0))},
                "spacing": float(f.get("spacing", 6.0)),
            })
            if f.get("rotation"):
                base["angle"] = float(f["rotation"])
        else:
            base.update({
                "type": "pattern",
                "patternType": ptype if ptype in ("dots", "lines", "grid", "hex") else "dots",
                "spacing": float(f.get("spacing", 3.0)),
                "region": "face",
            })
            if f.get("rotation"):
                base["angle"] = float(f["rotation"])
        return base

    if ftype in ("trama",):
        base.update({
            "type": "pattern",
            "patternType": "lines" if "line" in str(f.get("id", "")) else "dots",
            "spacing": float(f.get("spacing", 3.0)),
            "region": "face",
        })
        return base

    if ftype in ("logo", "svg-decor"):
        size = f.get("size", {})
        width = size.get("width", 20) if isinstance(size, dict) else float(size or 20)
        height = size.get("height", 0) if isinstance(size, dict) else 0
        base.update({"type": "icon", "width": float(width)})
        if height:
            base["height"] = float(height)
        if f.get("file"):
            base["svgAsset"] = str(f["file"])
        if f.get("_svgContent"):
            base["svgInline"] = str(f["_svgContent"])
        return base

    if ftype in ("frame", "guard", "guard-double"):
        base.update({
            "type": "shape",
            "shapeType": "frame",
            "strokeWidth": float(f.get("width", f.get("thickness", 1.0)) or 1.0),
            "inset": float(f.get("inset", 2.0)),
        })
        return base

    if ftype == "corner":
        base.update({
            "type": "shape",
            "shapeType": "corner-marks",
            "inset": float(f.get("inset", 3.0)),
            "length": float(f.get("length", 6.0)),
            "strokeWidth": float(f.get("thickness", 1.0)),
        })
        return base

    # Unknown feature type: drop rather than invent geometry
    return None


def _feature_base(f: Dict[str, Any], known_materials: set) -> Dict[str, Any]:
    pos = f.get("position", {}) or {}
    if isinstance(pos, list):
        pos = {"x": pos[0], "y": pos[1]}
    material = f.get("material", "base")
    if material not in known_materials:
        material = "base"
    base: Dict[str, Any] = {
        "id": str(f.get("id", "feature")),
        "transform": {"x": float(pos.get("x", 0)), "y": float(pos.get("y", 0))},
        "material": material,
        "relief": _relief(f.get("relief", {}) or {}),
    }
    if f.get("zIndex"):
        base["zOrder"] = int(f["zIndex"])
    if f.get("visible") is False:
        base["visible"] = False
    return base


def _relief(r: Dict[str, Any]) -> Dict[str, Any]:
    mode = r.get("mode", "emboss")
    if mode == "emboss":
        return {"mode": "emboss", "height": float(r.get("height") or 0.3)}
    if mode == "deboss":
        return {"mode": "deboss", "depth": float(r.get("depth") or 0.2)}
    if mode == "flush":
        return {"mode": "flush", "depth": float(r.get("depth") or 0.2)}
    if mode == "cut":
        return {"mode": "cut"}
    return {"mode": "emboss", "height": 0.3}


def _font(f: Dict[str, Any]) -> Dict[str, Any]:
    font: Dict[str, Any] = {
        "family": f.get("font", "sans-serif"),
        "size": float(f.get("fontSize", 3.0)),
    }
    weight = _FONT_STYLE_TO_WEIGHT.get(str(f.get("fontStyle", "")).lower())
    if weight and weight != 400:
        font["weight"] = weight
    return font


def _qr_fields(f: Dict[str, Any]) -> tuple:
    qr_type = f.get("qrType")
    if qr_type in ("url", "vcard", "wifi", "email", "text"):
        fields = {k: str(f[k]) for k in _QR_FIELD_KEYS if f.get(k)}
        if qr_type == "url" and not fields.get("url") and f.get("value"):
            fields["url"] = str(f["value"])
        if qr_type == "text" and not fields.get("text") and f.get("value"):
            fields["text"] = str(f["value"])
        return qr_type, fields or {"url": str(f.get("value", ""))}
    value = str(f.get("value", ""))
    if value.startswith(("http://", "https://", "{{")):
        return "url", {"url": value}
    if value.startswith("BEGIN:VCARD"):
        return "text", {"text": value}
    return ("url", {"url": value}) if value else ("text", {"text": ""})
