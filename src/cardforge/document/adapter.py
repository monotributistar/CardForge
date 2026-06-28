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


def _resolve_feature_vars(feature: dict, variables: dict, assets: dict) -> None:
    """Resolve {{var}} and {{assets.x}} in a feature dict in-place."""
    for key, value in list(feature.items()):
        if isinstance(value, str):
            feature[key] = _resolve_string(value, variables, assets)
        elif isinstance(value, list):
            feature[key] = [
                _resolve_string(v, variables, assets) if isinstance(v, str) else v
                for v in value
            ]


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
                qr_config = {
                    "enabled": True,
                    "type": "url",
                    "target": feat.get("value", doc.variables.get("website", "")),
                    "size": feat.get("size", 24),
                    "errorCorrection": "M",
                    "quietZone": 2,
                }
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
