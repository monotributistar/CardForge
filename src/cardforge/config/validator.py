"""Config validator — schema validation + range/consistency checks."""

import re
from typing import Any, Dict, List

from jsonschema import validate, ValidationError as JsonSchemaError


class ValidationError(Exception):
    """Raised when config fails validation."""

    pass


# ── JSON Schema ──────────────────────────────────────────────────────────────

CONFIG_SCHEMA = {
    "type": "object",
    "required": ["project", "manufacturing", "object", "faces"],
    "properties": {
        "project": {
            "type": "object",
            "required": ["name", "type", "version"],
            "properties": {
                "name": {"type": "string"},
                "type": {"type": "string"},
                "version": {"type": "string"},
                "description": {"type": "string"},
            },
        },
        "manufacturing": {
            "type": "object",
            "required": ["process", "nozzle", "layerHeight", "units"],
            "properties": {
                "process": {"type": "string"},
                "nozzle": {"type": "number"},
                "layerHeight": {"type": "number"},
                "units": {"type": "string"},
            },
        },
        "object": {
            "type": "object",
            "required": ["width", "height", "thickness"],
            "properties": {
                "width": {"type": "number"},
                "height": {"type": "number"},
                "thickness": {"type": "number"},
                "cornerRadius": {"type": "number"},
            },
        },
        "theme": {"type": "object"},
        "owner": {"type": "object"},
        "qr": {"type": "object"},
        "faces": {
            "type": "object",
            "properties": {
                "front": {"type": "object", "properties": {"features": {"type": "array"}}},
                "back": {"type": "object", "properties": {"features": {"type": "array"}}},
            },
        },
        "exports": {"type": "object"},
    },
}

FEATURE_SCHEMA = {
    "type": "object",
    "required": ["id", "type"],
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string"},
        "position": {"type": "object"},
        "size": {"type": "object"},
        "rotation": {"type": "number"},
        "material": {"type": "string"},
        "relief": {"type": "object"},
        "visibility": {"type": "string"},
        "zIndex": {"type": "number"},
        "source": {"type": "string"},
        "lines": {"type": "array"},
        "fontSize": {"type": "number"},
        "patternType": {"type": "string"},
        "text": {"type": "string"},
        "spacing": {"type": "number"},
        "frameStyle": {"type": "string"},
        "style": {"type": "string"},
    },
}


# ── Public API ────────────────────────────────────────────────────────────────

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a CardForge configuration.

    Checks performed:
        1. JSON Schema structure validation
        2. Range validation (dimensions, thickness, cornerRadius)
        3. Relief depth/height vs thickness
        4. QR code minimum size
        5. Template variable resolvability

    Args:
        config: Raw config dict.

    Returns:
        The validated config dict (unchanged if valid).

    Raises:
        ValidationError: With a description of all validation failures.
    """
    errors: List[str] = []

    # 1. Schema validation
    errors.extend(_validate_schema(config))

    if errors:
        raise ValidationError("; ".join(errors))

    # 2. Range validation
    errors.extend(_validate_ranges(config))

    # 3. Feature validation
    errors.extend(_validate_features(config))

    # 4. Template variable check
    errors.extend(_validate_template_vars(config))

    if errors:
        raise ValidationError("; ".join(errors))

    return config


# ── Schema validation ────────────────────────────────────────────────────────

def _validate_schema(config: Dict[str, Any]) -> List[str]:
    """Validate top-level structure against JSON Schema."""
    errors = []
    try:
        validate(instance=config, schema=CONFIG_SCHEMA)
    except JsonSchemaError as e:
        errors.append(f"Schema error: {e.message}")

    # Validate each feature against feature schema
    for face_name in ("front", "back"):
        face = config.get("faces", {}).get(face_name, {})
        for feature in face.get("features", []):
            try:
                validate(instance=feature, schema=FEATURE_SCHEMA)
            except JsonSchemaError as e:
                errors.append(
                    f"Feature '{feature.get('id', '?')}' on {face_name}: {e.message}"
                )

    return errors


# ── Range validation ─────────────────────────────────────────────────────────

def _validate_ranges(config: Dict[str, Any]) -> List[str]:
    """Validate numeric ranges for object dimensions."""
    errors = []
    obj = config.get("object", {})

    width = obj.get("width", 0)
    height = obj.get("height", 0)
    thickness = obj.get("thickness", 0)
    corner_radius = obj.get("cornerRadius", 0)

    if not isinstance(width, (int, float)):
        errors.append("object.width must be a number")
    elif width <= 0:
        errors.append(f"object.width must be > 0, got {width}")

    if not isinstance(height, (int, float)):
        errors.append("object.height must be a number")
    elif height <= 0:
        errors.append(f"object.height must be > 0, got {height}")

    if not isinstance(thickness, (int, float)):
        errors.append("object.thickness must be a number")
    elif thickness < 1.0:
        errors.append(f"object.thickness must be >= 1.0 mm, got {thickness}")
    elif thickness > 3.0:
        errors.append(f"object.thickness must be <= 3.0 mm, got {thickness}")

    if isinstance(corner_radius, (int, float)):
        max_radius = min(width, height) / 2
        if corner_radius > max_radius:
            errors.append(
                f"cornerRadius ({corner_radius}) exceeds half the smaller dimension ({max_radius})"
            )

    return errors


# ── Feature validation ───────────────────────────────────────────────────────

def _validate_features(config: Dict[str, Any]) -> List[str]:
    """Validate individual features for printing constraints."""
    errors = []
    thickness = config.get("object", {}).get("thickness", 1.8)
    half_thickness = thickness / 2

    # Check QR size
    qr_config = config.get("qr", {})
    if qr_config.get("enabled", False):
        qr_size = qr_config.get("size", 0)
        if isinstance(qr_size, (int, float)) and qr_size < 22:
            errors.append(
                f"QR size must be >= 22 mm for FDM 0.4mm, got {qr_size} mm"
            )

    # Check feature relief values
    for face_name in ("front", "back"):
        face = config.get("faces", {}).get(face_name, {})
        for feature in face.get("features", []):
            feature_id = feature.get("id", "?")
            relief = feature.get("relief", {})

            if not isinstance(relief, dict):
                continue

            mode = relief.get("mode", "flush")

            if mode == "emboss":
                height = relief.get("height", 0)
                if isinstance(height, (int, float)) and height > half_thickness:
                    errors.append(
                        f"Emboss height ({height} mm) on feature '{feature_id}' "
                        f"exceeds half thickness ({half_thickness} mm)"
                    )

            elif mode == "deboss":
                depth = relief.get("depth", 0)
                if isinstance(depth, (int, float)) and depth > half_thickness:
                    errors.append(
                        f"Deboss depth ({depth} mm) on feature '{feature_id}' "
                        f"exceeds half thickness ({half_thickness} mm)"
                    )

            elif mode == "cut":
                depth = relief.get("depth", 0)
                if isinstance(depth, (int, float)) and depth > thickness:
                    errors.append(
                        f"Cut depth ({depth} mm) on feature '{feature_id}' "
                        f"exceeds object thickness ({thickness} mm)"
                    )

    return errors


# ── Template variable validation ─────────────────────────────────────────────

_TEMPLATE_RE = re.compile(r"\{\{(.+?)\}\}")


def _validate_template_vars(config: Dict[str, Any]) -> List[str]:
    """Check that all template variables can resolve to config paths."""
    errors = []

    # Collect all available paths in the config
    available = _collect_paths(config)

    # Walk all string values looking for {{var}} patterns
    for face_name in ("front", "back"):
        face = config.get("faces", {}).get(face_name, {})
        for feature in face.get("features", []):
            lines = feature.get("lines", [])
            for line in lines:
                if not isinstance(line, str):
                    continue
                for match in _TEMPLATE_RE.finditer(line):
                    var_path = match.group(1)
                    if var_path not in available:
                        errors.append(
                            f"Unresolved variable '{{{{{var_path}}}}}' "
                            f"in feature '{feature.get('id', '?')}'"
                        )

    return errors


def _collect_paths(data: Any, prefix: str = "") -> set:
    """Collect all dot-notation paths from a nested dict."""
    paths = set()
    if isinstance(data, dict):
        for key, value in data.items():
            current = f"{prefix}.{key}" if prefix else key
            paths.add(current)
            paths.update(_collect_paths(value, current))
    return paths
