"""Document adapter — converts CardForgeDocument to legacy Card config."""

import re
from typing import Any, Dict

from cardforge.document.model import CardForgeDocument, DocumentObject


def resolve_document_variables(doc: CardForgeDocument) -> CardForgeDocument:
    """Resolve {{var}} and {{assets.x}} in all string values of the document."""
    import copy
    resolved = copy.deepcopy(doc)

    for obj in resolved.objects:
        for face_id in ("front", "back"):
            face = obj.faces.get(face_id, {})
            for feature in face.get("features", []):
                _resolve_feature_vars(feature, resolved.variables, resolved.assets)

    # Also resolve variables themselves (for export)
    return resolved


def _build_qr_value(qr_type: str, feat: dict, variables: dict) -> str:
    """Build the QR content string from type-specific fields."""
    if qr_type == "vcard":
        parts = ["BEGIN:VCARD", "VERSION:3.0"]
        if feat.get("vcard_name") or variables.get("name"):
            parts.append(f"FN:{feat.get('vcard_name') or variables.get('name', '')}")
        if feat.get("vcard_title") or variables.get("title"):
            parts.append(f"TITLE:{feat.get('vcard_title') or variables.get('title', '')}")
        if feat.get("vcard_phone") or variables.get("phone"):
            parts.append(f"TEL:{feat.get('vcard_phone') or variables.get('phone', '')}")
        if feat.get("vcard_email") or variables.get("email"):
            parts.append(f"EMAIL:{feat.get('vcard_email') or variables.get('email', '')}")
        if feat.get("vcard_website") or variables.get("website"):
            parts.append(f"URL:{feat.get('vcard_website') or variables.get('website', '')}")
        parts.append("END:VCARD")
        return "\n".join(parts)
    elif qr_type == "wifi":
        ssid = feat.get("wifi_ssid", variables.get("name", "MyWiFi"))
        pwd = feat.get("wifi_password", "")
        enc = feat.get("wifi_encryption", "WPA")
        return f"WIFI:T:{enc};S:{ssid};P:{pwd};;"
    elif qr_type == "email":
        addr = feat.get("email_address", variables.get("email", ""))
        subj = feat.get("email_subject", "")
        body = feat.get("email_body", "")
        mail = f"mailto:{addr}"
        params = []
        if subj:
            from urllib.parse import quote
            params.append(f"subject={quote(subj)}")
        if body:
            from urllib.parse import quote
            params.append(f"body={quote(body)}")
        if params:
            mail += "?" + "&".join(params)
        return mail
    elif qr_type == "text":
        return feat.get("text", feat.get("value", ""))
    else:  # url
        value = feat.get("url", feat.get("value", variables.get("website", "")))
        return value if value.startswith("http") else f"https://{value}" if value else ""


def _resolve_feature_vars(feat: dict, variables: dict, assets: dict) -> None:
    """Resolve {{var}} and {{assets.x}} in a feature dict in-place."""
    for key, value in list(feat.items()):
        if isinstance(value, str):
            feat[key] = _resolve_string(value, variables, assets)
        elif isinstance(value, list):
            feat[key] = [_resolve_string(v, variables, assets) if isinstance(v, str) else v for v in value]
        elif isinstance(value, dict):
            _resolve_feature_vars(value, variables, assets)


_VAR_RE = re.compile(r"\{\{(.+?)\}\}")


def _resolve_string(text: str, variables: dict, assets: dict) -> str:
    def _replace(match):
        path = match.group(1).strip()
        if path.startswith("assets."):
            key = path[7:]
            return assets.get(key, match.group(0))
        return variables.get(path, match.group(0))
    return _VAR_RE.sub(_replace, text)


def _normalize_feature(feat: dict) -> None:
    """Normalize feature fields for legacy config compatibility."""
    # Convert simple size number to {width, height} object
    if "size" in feat and isinstance(feat["size"], (int, float)):
        s = feat["size"]
        feat["size"] = {"width": s, "height": s}

    # Convert simple position [x, y] to {x, y} object if needed
    if "position" in feat and isinstance(feat["position"], (list, tuple)):
        x, y = feat["position"][0], feat["position"][1] if len(feat["position"]) > 1 else 0
        feat["position"] = {"x": x, "y": y}

    # QR features need source="qr" to reference top-level qr config
    if feat.get("type") == "qr" and "source" not in feat:
        feat["source"] = "qr"

    # Asset features need their type preserved for domain factory
    # Map guard types → frame, trama → pattern (Domain factory doesn't have guard/trama)
    asset_map = {"guard": "frame", "guard-double": "frame", "trama": "pattern"}
    if feat.get("type") in asset_map:
        feat["_original_type"] = feat["type"]
        feat["type"] = asset_map[feat["type"]]
        feat["source"] = "asset"
        if "size" not in feat:
            feat["size"] = {"width": 85, "height": 54}
        if feat["type"] == "frame":
            feat.setdefault("frameStyle", "border")
            feat.setdefault("width", 1.0)
            feat.setdefault("inset", 2.0)
        elif feat["type"] == "pattern":
            feat.setdefault("patternType", feat.get("_original_type") == "trama" and "dots" or "text-repeat")
            feat.setdefault("spacing", 6.0)
            feat.setdefault("rotation", 0)


def adapt_to_legacy_config(doc: CardForgeDocument, obj_index: int = 0) -> Dict[str, Any]:
    """Convert a CardForge document object to the legacy Card config format.

    Args:
        doc: Resolved CardForgeDocument.
        obj_index: Which object to adapt (default: 0, first object).

    Returns:
        Dict compatible with the existing Domain Factory (create_card_from_config).
    """
    if obj_index >= len(doc.objects):
        raise ValueError(f"Object index {obj_index} out of range ({len(doc.objects)} objects)")

    obj = doc.objects[obj_index]

    # Build owner from variables
    owner = {
        "name": doc.variables.get("name", ""),
        "title": doc.variables.get("title", ""),
        "phone": doc.variables.get("phone", ""),
        "email": doc.variables.get("email", ""),
        "website": doc.variables.get("website", ""),
        "github": doc.variables.get("github", ""),
        "linkedin": doc.variables.get("linkedin", ""),
    }

    # Build qr config from first qr feature on back or front
    qr_config = {"enabled": False}
    for face_id in ("back", "front"):
        face = obj.faces.get(face_id, {})
        for feat in face.get("features", []):
            if feat.get("type") == "qr":
                qr_type = feat.get("qrType", "url")
                qr_value = _build_qr_value(qr_type, feat, doc.variables)
                qr_config = {
                    "enabled": True,
                    "type": "url",
                    "target": qr_value,
                    "size": feat.get("size", 24),
                    "errorCorrection": "M",
                    "quietZone": 2,
                }
                # Normalize qr size if it's a number
                if isinstance(qr_config["size"], (int, float)):
                    s = qr_config["size"]
                    qr_config["size"] = {"width": s, "height": s}
                break
        if qr_config["enabled"]:
            break

    # Normalize features: convert simple size numbers to {width, height} objects
    # and convert simple position arrays to {x, y} objects
    for face_id in ("front", "back"):
        face = obj.faces.get(face_id, {})
        for feat in face.get("features", []):
            _normalize_feature(feat)

    return {
        "project": {
            "name": doc.metadata.id or doc.metadata.name,
            "type": obj.type,
            "version": doc.metadata.version,
        },
        "manufacturing": {
            "process": doc.manufacturing.process,
            "nozzle": doc.manufacturing.nozzle,
            "layerHeight": doc.manufacturing.layer_height,
            "units": "mm",
        },
        "object": {
            "width": obj.width,
            "height": obj.height,
            "thickness": obj.thickness,
            "cornerRadius": obj.corner_radius,
        },
        "theme": obj.theme,
        "owner": owner,
        "qr": qr_config,
        "faces": obj.faces,
        "exports": {
            "singleStl": doc.exports.single_stl,
            "colorSeparatedStl": doc.exports.color_separated_stl,
            "threeMf": doc.exports.three_mf,
            "previewSvg": doc.exports.preview,
            "previewPng": False,
        },
    }
