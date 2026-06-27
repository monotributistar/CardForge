"""Factory — converts a resolved config dict into a Card domain object."""

from typing import Any, Dict

from cardforge.domain.card import Card
from cardforge.domain.face import Face
from cardforge.domain.feature import (
    Feature,
    TextBlockFeature,
    QRCodeFeature,
    PatternFeature,
    LogoFeature,
    FrameFeature,
    CornerDecorationFeature,
)
from cardforge.domain.geometry import Position, Size
from cardforge.domain.layer import Layer
from cardforge.domain.material import Material, DEFAULT_MATERIALS
from cardforge.domain.relief import Relief, ReliefMode
from cardforge.domain.build_context import BuildContext, ManufacturingSettings


class FactoryError(Exception):
    """Raised when config cannot be converted to domain objects."""

    pass


def create_card_from_config(
    config: Dict[str, Any],
    context: BuildContext = None,
) -> Card:
    """Convert a resolved config dict into a Card domain object.

    Args:
        config: Resolved config dict (variables already substituted).
        context: Optional BuildContext for materials and settings.

    Returns:
        A fully populated Card instance.

    Raises:
        FactoryError: If config is missing required fields or has unknown types.
    """
    if context is None:
        context = BuildContext()

    # Extract manufacturing settings from config
    mfg = config.get("manufacturing", {})
    context.manufacturing = ManufacturingSettings(
        process=mfg.get("process", "fdm"),
        nozzle=mfg.get("nozzle", 0.4),
        layer_height=mfg.get("layerHeight", 0.2),
        units=mfg.get("units", "mm"),
    )

    # Build materials from theme or defaults
    materials = _build_materials(config.get("theme", {}), context)

    # Extract object parameters
    obj = config["object"]
    card = Card(
        id=config.get("project", {}).get("name", "untitled").lower().replace(" ", "_"),
        name=config.get("project", {}).get("name", "Untitled"),
        width=obj["width"],
        height=obj["height"],
        thickness=obj["thickness"],
        corner_radius=obj.get("cornerRadius", 4.0),
        object_type=config.get("project", {}).get("type", "business-card"),
        materials=materials,
    )

    # Build faces
    faces_config = config.get("faces", {})
    for face_id in ("front", "back"):
        face_config = faces_config.get(face_id, {})
        if not face_config:
            continue

        face = Face(
            id=face_id,
            name=face_id.capitalize(),
            width=card.width,
            height=card.height,
        )

        # Create default layer
        layer = Layer(id="content", name="Content", role="content", z_index=0)

        # Build features
        features_data = face_config.get("features", [])
        for feat_data in features_data:
            feature = _build_feature(feat_data, face_id, materials, context, config)
            if feature:
                layer.features.append(feature)

        face.layers.append(layer)
        card.faces[face_id] = face

    return card


def _build_materials(theme: dict, context: BuildContext) -> Dict[str, Material]:
    """Build material dict from theme config, falling back to defaults."""
    materials = dict(DEFAULT_MATERIALS)

    # Theme can override or add materials
    if theme:
        theme_mapping = {
            "base": theme.get("baseColor", "black"),
            "text": theme.get("textColor", "white"),
            "accent": theme.get("accentColor", "gold"),
        }
        for mat_id, color_name in theme_mapping.items():
            if mat_id in materials:
                materials[mat_id].color = _color_name_to_hex(color_name)

    return materials


def _color_name_to_hex(name: str) -> str:
    """Convert common color names to hex. Falls back to original string."""
    mapping = {
        "black": "#1a1a1a",
        "white": "#ffffff",
        "gold": "#ffd700",
        "silver": "#c0c0c0",
        "red": "#ff0000",
        "blue": "#0000ff",
        "green": "#00ff00",
    }
    return mapping.get(name.lower(), name)


def _build_relief(relief_data: dict) -> Relief:
    """Build a Relief object from config dict."""
    if not relief_data:
        return Relief.flush()

    mode_str = relief_data.get("mode", "flush")
    try:
        mode = ReliefMode(mode_str)
    except ValueError:
        raise FactoryError(f"Unknown relief mode: {mode_str}")

    if mode == ReliefMode.EMBOSS:
        return Relief.emboss(relief_data.get("height", 0.4))
    elif mode == ReliefMode.DEBOSS:
        return Relief.deboss(relief_data.get("depth", 0.2))
    elif mode == ReliefMode.CUT:
        return Relief.cut(relief_data.get("depth", 0.5))
    else:
        return Relief.flush()


def _build_feature(
    data: dict,
    face_id: str,
    materials: Dict[str, Material],
    context: BuildContext,
    config: Dict[str, Any],
) -> Feature:
    """Build a Feature subclass from config dict."""
    feat_type = data.get("type", "")
    feat_id = data.get("id", "unknown")

    # Resolve material
    material_id = data.get("material", "base")
    material = materials.get(material_id)
    if material is None and material_id:
        context.add_warning(f"Unknown material '{material_id}' for feature '{feat_id}'")
        material = materials.get("base")

    # Resolve relief
    try:
        relief = _build_relief(data.get("relief", {}))
    except FactoryError as e:
        context.add_error(str(e), feature_id=feat_id)
        relief = Relief.flush()

    # Resolve position
    pos = data.get("position", {})
    position = Position(
        x=float(pos.get("x", 0)),
        y=float(pos.get("y", 0)),
    )

    # Resolve size
    sz = data.get("size", {})
    size = Size(
        width=float(sz.get("width", 0)),
        height=float(sz.get("height", 0)),
    )

    # Common base params
    base = {
        "id": feat_id,
        "name": data.get("name", feat_id),
        "face": face_id,
        "position": position,
        "size": size,
        "material": material,
        "relief": relief,
        "visible": data.get("visibility", "visible") != "hidden",
        "z_index": int(data.get("zIndex", 0)),
    }

    # Dispatch to concrete type
    if feat_type == "text-block":
        return TextBlockFeature(
            **base,
            lines=data.get("lines", []),
            font=data.get("font", "Montserrat"),
            font_size=float(data.get("fontSize", 3.0)),
            font_style=data.get("fontStyle", "bold"),
            align=data.get("align", "left"),
            line_height=float(data.get("lineHeight", 1.4)),
        )

    elif feat_type == "qr":
        # QR might reference top-level qr config via source="qr"
        # or have inline params with qrType field
        if data.get("source") == "qr":
            top_qr = config.get("qr", {})
            qr_data_type = top_qr.get("type", "vcard") if top_qr else "vcard"
            qr_target = top_qr.get("target", "owner")
            qr_error = top_qr.get("errorCorrection", "M")
            qr_quiet = float(top_qr.get("quietZone", 2.0))
            # Size comes from position/size in the feature data itself
        else:
            qr_data_type = data.get("qrType", "vcard")
            qr_target = data.get("target", "owner")
            qr_error = data.get("errorCorrection", "M")
            qr_quiet = float(data.get("quietZone", 2.0))
        return QRCodeFeature(
            **base,
            qr_type=qr_data_type,
            target=qr_target,
            error_correction=qr_error,
            quiet_zone=qr_quiet,
        )

    elif feat_type == "pattern":
        return PatternFeature(
            **base,
            pattern_type=data.get("patternType", "text-repeat"),
            text=data.get("text", ""),
            spacing=float(data.get("spacing", 10.0)),
            rotation_degrees=float(data.get("rotation", 0)),
        )

    elif feat_type == "logo":
        return LogoFeature(
            **base,
            svg_file=data.get("file", ""),
        )

    elif feat_type == "frame":
        return FrameFeature(
            **base,
            frame_style=data.get("frameStyle", "border"),
            frame_width=float(data.get("width", 2.0)),
            inset=float(data.get("inset", 0)),
        )

    elif feat_type == "corner":
        return CornerDecorationFeature(
            **base,
            corner_style=data.get("style", "round"),
            radius=float(data.get("radius", 4.0)),
        )

    else:
        raise FactoryError(f"Unknown feature type: '{feat_type}' (feature '{feat_id}')")
