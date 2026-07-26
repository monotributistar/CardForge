"""CardForge document schema v2 — typed model.

The v2 document is the single editable source of truth. It compiles directly
to the geometry kernel (no intermediate Card domain, no legacy config).

Structure:
    cardforge: "2.0"
    meta:      id, name, description?, created?, modified?
    object:    outline (rect | rounded-rect | path) + thickness
    materials: palette [{id, name, color, slot?, role?}] — slot maps to the
               multicolor system (CFS/AMS) filament slot
    variables: {{var}} substitutions for feature text
    assets:    asset id → file path (SVG icons, fonts)
    faces:     front / back, each a list of features

Feature types: text-block, text-pattern, pattern, qr, icon, shape, hole, pocket.
Relief modes:  emboss, deboss, flush, cut, deboss-backed — any feature can use
               any relief mode (a QR can be a through-cut, text can be a
               backed cavity, etc.), except `hole` and `pocket`, which own
               their own z geometry and carry a fixed `{"mode": "cut"}`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "2.0"
FEATURE_TYPES = ("text-block", "text-pattern", "pattern", "qr", "icon", "shape",
                 "hole", "pocket")
RELIEF_MODES = ("emboss", "deboss", "flush", "cut", "deboss-backed")

# Pocket fit defaults (mm). An FDM bore prints undersized, so a magnet/tag
# needs the cavity opened up to go in at all — these are the values a pocket
# gets when the document does not state its own. They are always written back
# out, so the tolerance a part was built with stays visible in the file.
DEFAULT_POCKET_CLEARANCE = 0.2        # added to the insert diameter
DEFAULT_POCKET_DEPTH_CLEARANCE = 0.1  # added to the insert thickness

_SCHEMA_PATH = Path(__file__).parent / "schema" / "v2.schema.json"


class DocumentValidationError(Exception):
    """Raised when a document fails v2 schema or referential validation."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


# ── Value objects ──────────────────────────────────────────────────────────

@dataclass
class Meta:
    id: str
    name: str
    description: str = ""
    created: str = ""
    modified: str = ""


@dataclass
class Outline:
    """Object outline. type: rect | rounded-rect | circle | path.

    rounded-rect: uniform `radius`, or per-corner `corners` {tl,tr,br,bl}
    (missing corners fall back to `radius`).
    circle: `diameter` (width/height are derived == diameter).
    path: `svg_inline` (full SVG markup — preferred: transforms, all shape
    elements, and multicolor supported) or `svg_path` (a raw `d` string).
    With svg_inline, `color_map` {svg hex → material id} extrudes each fill
    color in its own material; unmapped regions stay base.

    `color_depth` limits the colors to a layer that deep, measured from the
    coloured face (`color_face`: front | back | both) — the rest of the body
    stays base material, so the opposite face is a clean single-colour canvas
    for text/QR. 0 = the colors run through the full thickness.
    """

    type: str
    width: float
    height: float
    radius: float = 0.0
    corners: Optional[Dict[str, float]] = None
    diameter: float = 0.0
    svg_path: str = ""
    svg_inline: str = ""
    color_map: Dict[str, str] = field(default_factory=dict)
    color_depth: float = 0.0
    color_face: str = "front"

    def corner_radii(self) -> Dict[str, float]:
        """Effective per-corner radii, filling from `radius` where unset."""
        c = self.corners or {}
        return {k: float(c.get(k, self.radius)) for k in ("tl", "tr", "br", "bl")}


@dataclass
class Fill:
    """Base body fill. type: solid | lattice(pattern, spacing, line_width, border)."""

    type: str = "solid"
    pattern: str = "grid"
    spacing: float = 4.0
    line_width: float = 1.0
    border: float = 2.0  # solid rim width around the lattice


@dataclass
class ObjectSpec:
    outline: Outline
    thickness: float
    fill: Fill = field(default_factory=Fill)


@dataclass
class Material:
    id: str
    name: str
    color: str  # #rrggbb, drives preview AND 3MF basematerials displaycolor
    slot: Optional[int] = None  # CFS/AMS filament slot (1-based)
    role: str = ""


@dataclass
class Transform:
    x: float
    y: float
    rotation: float = 0.0  # degrees, around feature anchor
    scale: float = 1.0


@dataclass
class Relief:
    """Z-axis treatment. Exactly one of height/depth applies per mode:

    emboss{height}  — raised above the surface
    deboss{depth}   — cavity into the base
    flush{depth}    — inlay: sunk into the base, top coplanar with surface
    cut{}           — through-hole across the whole thickness
    deboss-backed{depth, floor_material, floor_thickness}
                    — cavity whose floor is a different material
    """

    mode: str
    height: float = 0.0
    depth: float = 0.0
    floor_material: str = ""
    floor_thickness: float = 0.0


@dataclass
class Backing:
    """Support pad under a feature so it isn't left floating.

    mode: 'auto'  — the compiler adds a pad only when the feature would float
                    (e.g. over a lattice base); no-op on a solid base.
          'on'    — always add a pad.
          'off'   — never add a pad.
    thickness: pad thickness in mm. 0 = auto: full object thickness over a
               lattice (the pad must reach the bed), a thin surface plate on
               a solid base (a through-column would show on the other face).
    material: pad material id (defaults to the base material).
    padding: extra margin (mm) around the feature bounds for the plate
             (QR features default to their quiet zone).
    shape: plate outline — 'rect' (bounds + padding) or 'circle' (centered
           on the bounds, diameter = larger bounds side + 2*padding).
    """

    mode: str = "auto"
    thickness: float = 0.0
    material: str = ""
    padding: float = 0.0
    shape: str = "rect"


@dataclass
class Font:
    family: str
    size: float  # mm (cap-height-relative sizing handled by kernel)
    weight: Optional[float] = None
    italic: bool = False
    axes: Dict[str, float] = field(default_factory=dict)  # variable font axes


@dataclass
class Feature:
    """A single element on a face. Type-specific fields live in `params`."""

    id: str
    type: str
    transform: Transform
    material: str
    relief: Relief
    name: str = ""
    z_order: int = 0
    visible: bool = True
    backing: Optional[Backing] = None                       # support pad
    # type-specific:
    lines: List[str] = field(default_factory=list)          # text-block
    font: Optional[Font] = None                              # text-block, text-pattern
    align: str = "left"                                      # text-block
    line_height: float = 1.4                                 # text-block
    text: str = ""                                           # text-pattern
    spacing: float = 0.0                                     # text-pattern, pattern
    spacing_y: float = 0.0                                   # text-pattern (0 → same as spacing)
    angle: float = 0.0                                       # text-pattern, pattern
    pattern_type: str = ""                                   # pattern
    element_size: float = 0.0                                # pattern
    region: str = "bounds"                                   # pattern: face | bounds
    qr_type: str = ""                                        # qr
    fields: Dict[str, str] = field(default_factory=dict)     # qr
    size: float = 0.0                                        # qr
    error_correction: str = "M"                              # qr
    quiet_zone: float = 2.0                                  # qr
    svg_asset: str = ""                                      # icon
    svg_inline: str = ""                                     # icon
    color_map: Dict[str, str] = field(default_factory=dict)  # icon: svg hex → material id
    width: float = 0.0                                       # icon, pattern(bounds), shape
    height: float = 0.0                                      # icon, pattern(bounds), shape
    shape_type: str = ""                                     # shape
    radius: float = 0.0                                      # shape
    diameter: float = 0.0                                    # shape
    stroke_width: float = 0.0                                # shape frame/corner-marks/ring
    inset: float = 0.0                                       # shape frame/corner-marks
    length: float = 0.0                                      # shape corner-marks
    svg_path: str = ""                                       # shape path
    hole_type: str = ""                                      # hole: circle | slot
    tab: bool = False                                        # hole: add a material lug
    tab_margin: float = 0.0                                  # hole: lug ring width (0 → 3mm)
    # pocket — blind cavity sized to hold an insert (magnet, RFID/NFC tag).
    # `diameter`/`depth` are the INSERT's nominal size; the cavity actually
    # cut is (diameter + clearance) × (depth + depth_clearance), so the fit is
    # tuned without lying about what goes in it. `ceiling` is the lid left
    # over the pocket, measured from the face: 0 opens it at the surface,
    # anything else buries the insert (the print pauses to drop it in).
    pocket_type: str = ""                                    # pocket: circle
    insert: str = ""                                         # pocket: magnet | rfid | other
    depth: float = 0.0                                       # pocket: insert thickness
    clearance: float = 0.0                                   # pocket: diametral slack
    depth_clearance: float = 0.0                             # pocket: depth slack
    ceiling: float = 0.0                                     # pocket: lid over the cavity

    # ── Pocket geometry (nominal + tolerance) ──────────────────────────
    @property
    def pocket_bore(self) -> float:
        """Diameter actually cut (mm)."""
        return self.diameter + self.clearance

    @property
    def pocket_depth(self) -> float:
        """Cavity depth actually cut (mm)."""
        return self.depth + self.depth_clearance


@dataclass
class Face:
    features: List[Feature] = field(default_factory=list)


@dataclass
class Manufacturing:
    process: str = "fdm"
    profile: str = "fdm-standard"
    nozzle: float = 0.4
    layer_height: float = 0.2


@dataclass
class DocumentV2:
    meta: Meta
    object: ObjectSpec
    materials: List[Material]
    faces: Dict[str, Face]
    variables: Dict[str, str] = field(default_factory=dict)
    assets: Dict[str, str] = field(default_factory=dict)
    manufacturing: Manufacturing = field(default_factory=Manufacturing)

    # ── Convenience ────────────────────────────────────────────────────
    def material_by_id(self, mat_id: str) -> Optional[Material]:
        return next((m for m in self.materials if m.id == mat_id), None)

    @property
    def base_material(self) -> Material:
        return next((m for m in self.materials if m.role == "base"), self.materials[0])

    def all_features(self):
        for face_id, face in self.faces.items():
            for feat in face.features:
                yield face_id, feat

    # ── Serialization ──────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentV2":
        _sanitize_relief(data)
        validate_v2(data)  # raises DocumentValidationError

        meta = Meta(
            id=data["meta"]["id"],
            name=data["meta"]["name"],
            description=data["meta"].get("description", ""),
            created=data["meta"].get("created", ""),
            modified=data["meta"].get("modified", ""),
        )
        o = data["object"]
        ol = o["outline"]
        diameter = ol.get("diameter", 0.0)
        outline = Outline(
            type=ol["type"],
            width=ol.get("width", diameter),
            height=ol.get("height", diameter),
            radius=ol.get("radius", 0.0),
            corners=dict(ol["corners"]) if ol.get("corners") else None,
            diameter=diameter,
            svg_path=ol.get("svgPath", ""),
            svg_inline=ol.get("svgInline", ""),
            color_map=dict(ol.get("colorMap", {})),
            color_depth=ol.get("colorDepth", 0.0),
            color_face=ol.get("colorFace", "front"),
        )
        fd = o.get("fill") or {"type": "solid"}
        fill = Fill(
            type=fd.get("type", "solid"),
            pattern=fd.get("pattern", "grid"),
            spacing=fd.get("spacing", 4.0),
            line_width=fd.get("lineWidth", 1.0),
            border=fd.get("border", 2.0),
        )
        materials = [
            Material(
                id=m["id"], name=m["name"], color=m["color"],
                slot=m.get("slot"), role=m.get("role", ""),
            )
            for m in data["materials"]
        ]
        mf = data.get("manufacturing", {})
        manufacturing = Manufacturing(
            process=mf.get("process", "fdm"),
            profile=mf.get("profile", "fdm-standard"),
            nozzle=mf.get("nozzle", 0.4),
            layer_height=mf.get("layerHeight", 0.2),
        )
        faces = {
            face_id: Face(features=[_feature_from_dict(f) for f in face.get("features", [])])
            for face_id, face in data.get("faces", {}).items()
        }
        return cls(
            meta=meta,
            object=ObjectSpec(outline=outline, thickness=o["thickness"], fill=fill),
            materials=materials,
            faces=faces,
            variables=dict(data.get("variables", {})),
            assets=dict(data.get("assets", {})),
            manufacturing=manufacturing,
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "cardforge": SCHEMA_VERSION,
            "meta": {"id": self.meta.id, "name": self.meta.name},
            "object": {
                "outline": _outline_to_dict(self.object.outline),
                "thickness": self.object.thickness,
                **({"fill": _fill_to_dict(self.object.fill)}
                   if self.object.fill.type != "solid" else {}),
            },
            "materials": [
                {k: v for k, v in {
                    "id": m.id, "name": m.name, "color": m.color,
                    "slot": m.slot, "role": m.role or None,
                }.items() if v is not None}
                for m in self.materials
            ],
            "variables": dict(self.variables),
            "assets": dict(self.assets),
            "manufacturing": {
                "process": self.manufacturing.process,
                "profile": self.manufacturing.profile,
                "nozzle": self.manufacturing.nozzle,
                "layerHeight": self.manufacturing.layer_height,
            },
            "faces": {
                face_id: {"features": [_feature_to_dict(f) for f in face.features]}
                for face_id, face in self.faces.items()
            },
        }
        for k in ("description", "created", "modified"):
            v = getattr(self.meta, k)
            if v:
                out["meta"][k] = v
        return out


# ── Validation ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_schema() -> Dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


# Params each relief mode accepts. Mode switches in older Studio builds left
# the previous mode's params behind (e.g. emboss's `height` after switching
# to deboss), which the strict schema then rejected — documents saved that
# way must still open, so loading prunes params foreign to the active mode.
_RELIEF_PARAMS = {
    "emboss": {"height"},
    "deboss": {"depth"},
    "flush": {"depth"},
    "cut": set(),
    "deboss-backed": {"depth", "floorMaterial", "floorThickness"},
}


def _sanitize_relief(data: Dict[str, Any]) -> None:
    for face in (data.get("faces") or {}).values():
        for feat in face.get("features", []) if isinstance(face, dict) else []:
            relief = feat.get("relief")
            if not isinstance(relief, dict):
                continue
            allowed = _RELIEF_PARAMS.get(relief.get("mode"))
            if allowed is None:
                continue  # unknown mode — let validation report it
            for key in [k for k in relief if k != "mode" and k not in allowed]:
                del relief[key]


def validate_v2(data: Dict[str, Any]) -> None:
    """Validate a raw dict against the v2 JSON Schema + referential rules.

    Raises DocumentValidationError listing every problem found.
    """
    import jsonschema

    errors: List[str] = []
    validator = jsonschema.Draft202012Validator(_load_schema())
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{loc}: {err.message}")

    if not errors:
        # Referential integrity: every material reference must exist
        mat_ids = {m["id"] for m in data.get("materials", [])}
        ol = data.get("object", {}).get("outline", {})
        for svg_hex, mat in ol.get("colorMap", {}).items():
            if mat not in mat_ids:
                errors.append(
                    f"object/outline: colorMap {svg_hex} → unknown material '{mat}'")
        # A colour layer as deep as the body is not a layer — it is the
        # legacy through-column, which is what omitting colorDepth means.
        depth = ol.get("colorDepth")
        thickness = data.get("object", {}).get("thickness")
        if depth and isinstance(thickness, (int, float)) and depth >= thickness:
            errors.append(
                f"object/outline: colorDepth {depth} >= thickness {thickness} — "
                "omit colorDepth for full-thickness colors")
        for face_id, face in data.get("faces", {}).items():
            for feat in face.get("features", []):
                fid = feat.get("id", "?")
                if feat.get("material") not in mat_ids:
                    errors.append(
                        f"faces/{face_id}/{fid}: unknown material '{feat.get('material')}'")
                bm = (feat.get("backing") or {}).get("material")
                if bm and bm not in mat_ids:
                    errors.append(
                        f"faces/{face_id}/{fid}: unknown backing material '{bm}'")
                relief = feat.get("relief", {})
                fm = relief.get("floorMaterial")
                if fm and fm not in mat_ids:
                    errors.append(
                        f"faces/{face_id}/{fid}: unknown floorMaterial '{fm}'")
                if relief.get("mode") == "deboss-backed" and fm == feat.get("material"):
                    errors.append(
                        f"faces/{face_id}/{fid}: floorMaterial must differ from feature material")
                for svg_hex, mat in feat.get("colorMap", {}).items():
                    if mat not in mat_ids:
                        errors.append(
                            f"faces/{face_id}/{fid}: colorMap {svg_hex} → unknown material '{mat}'")
        # Duplicate feature ids
        seen: set = set()
        for face_id, face in data.get("faces", {}).items():
            for feat in face.get("features", []):
                fid = feat.get("id")
                if fid in seen:
                    errors.append(f"faces/{face_id}/{fid}: duplicate feature id")
                seen.add(fid)

    if errors:
        raise DocumentValidationError(errors)


def is_v2(data: Dict[str, Any]) -> bool:
    return data.get("cardforge") == SCHEMA_VERSION


# ── dict ↔ dataclass helpers ───────────────────────────────────────────────

def _outline_to_dict(o: Outline) -> Dict[str, Any]:
    if o.type == "circle":
        return {"type": "circle", "diameter": o.diameter or o.width}
    d: Dict[str, Any] = {"type": o.type, "width": o.width, "height": o.height}
    if o.type == "rounded-rect":
        d["radius"] = o.radius
        if o.corners:
            d["corners"] = dict(o.corners)
    if o.type == "path":
        if o.svg_path:
            d["svgPath"] = o.svg_path
        if o.svg_inline:
            d["svgInline"] = o.svg_inline
        if o.color_map:
            d["colorMap"] = dict(o.color_map)
        if o.color_depth:
            d["colorDepth"] = o.color_depth
            if o.color_face and o.color_face != "front":
                d["colorFace"] = o.color_face
    return d


def _fill_to_dict(f: "Fill") -> Dict[str, Any]:
    if f.type == "solid":
        return {"type": "solid"}
    d: Dict[str, Any] = {"type": "lattice", "pattern": f.pattern, "spacing": f.spacing}
    if f.line_width:
        d["lineWidth"] = f.line_width
    if f.border:
        d["border"] = f.border
    return d


def _backing_to_dict(b: "Backing") -> Dict[str, Any]:
    d: Dict[str, Any] = {"mode": b.mode}
    if b.thickness:
        d["thickness"] = b.thickness
    if b.material:
        d["material"] = b.material
    if b.padding:
        d["padding"] = b.padding
    if b.shape and b.shape != "rect":
        d["shape"] = b.shape
    return d


def _feature_from_dict(f: Dict[str, Any]) -> Feature:
    t = f["transform"]
    r = f["relief"]
    font = None
    if "font" in f:
        font = Font(
            family=f["font"]["family"],
            size=f["font"]["size"],
            weight=f["font"].get("weight"),
            italic=f["font"].get("italic", False),
            axes=dict(f["font"].get("axes", {})),
        )
    return Feature(
        id=f["id"],
        type=f["type"],
        name=f.get("name", ""),
        transform=Transform(
            x=t["x"], y=t["y"],
            rotation=t.get("rotation", 0.0),
            scale=t.get("scale", 1.0),
        ),
        material=f["material"],
        relief=Relief(
            mode=r["mode"],
            height=r.get("height", 0.0),
            depth=r.get("depth", 0.0),
            floor_material=r.get("floorMaterial", ""),
            floor_thickness=r.get("floorThickness", 0.0),
        ),
        z_order=f.get("zOrder", 0),
        visible=f.get("visible", True),
        backing=Backing(
            mode=f["backing"].get("mode", "auto"),
            thickness=f["backing"].get("thickness", 0.0),
            material=f["backing"].get("material", ""),
            padding=f["backing"].get("padding", 0.0),
            shape=f["backing"].get("shape", "rect"),
        ) if f.get("backing") else None,
        lines=list(f.get("lines", [])),
        font=font,
        align=f.get("align", "left"),
        line_height=f.get("lineHeight", 1.4),
        text=f.get("text", ""),
        spacing=f.get("spacing", 0.0),
        spacing_y=f.get("spacingY", 0.0),
        angle=f.get("angle", 0.0),
        pattern_type=f.get("patternType", ""),
        element_size=f.get("elementSize", 0.0),
        region=f.get("region", "bounds"),
        qr_type=f.get("qrType", ""),
        fields=dict(f.get("fields", {})),
        size=f.get("size", 0.0),
        error_correction=f.get("errorCorrection", "M"),
        quiet_zone=f.get("quietZone", 2.0),
        svg_asset=f.get("svgAsset", ""),
        svg_inline=f.get("svgInline", ""),
        color_map=dict(f.get("colorMap", {})),
        width=f.get("width", 0.0),
        height=f.get("height", 0.0),
        shape_type=f.get("shapeType", ""),
        radius=f.get("radius", 0.0),
        diameter=f.get("diameter", 0.0),
        stroke_width=f.get("strokeWidth", 0.0),
        inset=f.get("inset", 0.0),
        length=f.get("length", 0.0),
        svg_path=f.get("svgPath", ""),
        hole_type=f.get("holeType", ""),
        tab=f.get("tab", False),
        tab_margin=f.get("tabMargin", 0.0),
        pocket_type=f.get("pocketType", ""),
        insert=f.get("insert", ""),
        depth=f.get("depth", 0.0),
        # An omitted clearance is not "zero clearance" — it is "no tolerance
        # stated", which for a press-in insert means the sane default.
        clearance=f.get("clearance", DEFAULT_POCKET_CLEARANCE
                        if f.get("type") == "pocket" else 0.0),
        depth_clearance=f.get("depthClearance", DEFAULT_POCKET_DEPTH_CLEARANCE
                              if f.get("type") == "pocket" else 0.0),
        ceiling=f.get("ceiling", 0.0),
    )


def _feature_to_dict(f: Feature) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id": f.id,
        "type": f.type,
        "transform": {"x": f.transform.x, "y": f.transform.y},
        "material": f.material,
        "relief": _relief_to_dict(f.relief),
    }
    if f.transform.rotation:
        d["transform"]["rotation"] = f.transform.rotation
    if f.transform.scale != 1.0:
        d["transform"]["scale"] = f.transform.scale
    if f.name:
        d["name"] = f.name
    if f.z_order:
        d["zOrder"] = f.z_order
    if not f.visible:
        d["visible"] = False
    if f.backing is not None:
        d["backing"] = _backing_to_dict(f.backing)

    if f.type == "text-block":
        d["lines"] = list(f.lines)
        d["font"] = _font_to_dict(f.font)
        if f.align != "left":
            d["align"] = f.align
        if f.line_height != 1.4:
            d["lineHeight"] = f.line_height
    elif f.type == "text-pattern":
        d["text"] = f.text
        d["font"] = _font_to_dict(f.font)
        d["spacing"] = f.spacing
        if f.spacing_y:
            d["spacingY"] = f.spacing_y
        if f.angle:
            d["angle"] = f.angle
    elif f.type == "pattern":
        d["patternType"] = f.pattern_type
        d["spacing"] = f.spacing
        if f.spacing_y:
            d["spacingY"] = f.spacing_y
        if f.angle:
            d["angle"] = f.angle
        if f.element_size:
            d["elementSize"] = f.element_size
        if f.region != "bounds":
            d["region"] = f.region
        if f.width:
            d["width"] = f.width
        if f.height:
            d["height"] = f.height
        if f.svg_inline:
            d["svgInline"] = f.svg_inline
        if f.color_map:
            d["colorMap"] = dict(f.color_map)
    elif f.type == "qr":
        d["qrType"] = f.qr_type
        d["fields"] = dict(f.fields)
        d["size"] = f.size
        if f.error_correction != "M":
            d["errorCorrection"] = f.error_correction
        if f.quiet_zone != 2.0:
            d["quietZone"] = f.quiet_zone
    elif f.type == "icon":
        if f.svg_asset:
            d["svgAsset"] = f.svg_asset
        if f.svg_inline:
            d["svgInline"] = f.svg_inline
        d["width"] = f.width
        if f.height:
            d["height"] = f.height
        if f.color_map:
            d["colorMap"] = dict(f.color_map)
    elif f.type == "shape":
        d["shapeType"] = f.shape_type
        for key, val in (
            ("width", f.width), ("height", f.height), ("radius", f.radius),
            ("diameter", f.diameter), ("strokeWidth", f.stroke_width),
            ("inset", f.inset), ("length", f.length),
        ):
            if val:
                d[key] = val
        if f.svg_path:
            d["svgPath"] = f.svg_path
    elif f.type == "hole":
        d["holeType"] = f.hole_type
        for key, val in (
            ("diameter", f.diameter), ("width", f.width), ("height", f.height),
            ("tabMargin", f.tab_margin),
        ):
            if val:
                d[key] = val
        if f.tab:
            d["tab"] = True
    elif f.type == "pocket":
        d["pocketType"] = f.pocket_type or "circle"
        d["diameter"] = f.diameter
        d["depth"] = f.depth
        # Tolerances are always written, including 0 — the fit a part was
        # built with must survive a round-trip, not fall back to a default.
        d["clearance"] = f.clearance
        d["depthClearance"] = f.depth_clearance
        if f.insert:
            d["insert"] = f.insert
        if f.ceiling:
            d["ceiling"] = f.ceiling
    return d


def _relief_to_dict(r: Relief) -> Dict[str, Any]:
    if r.mode == "emboss":
        return {"mode": "emboss", "height": r.height}
    if r.mode in ("deboss", "flush"):
        return {"mode": r.mode, "depth": r.depth}
    if r.mode == "cut":
        return {"mode": "cut"}
    if r.mode == "deboss-backed":
        return {
            "mode": "deboss-backed", "depth": r.depth,
            "floorMaterial": r.floor_material, "floorThickness": r.floor_thickness,
        }
    raise ValueError(f"unknown relief mode: {r.mode}")


def _font_to_dict(font: Optional[Font]) -> Dict[str, Any]:
    assert font is not None, "text feature requires font"
    d: Dict[str, Any] = {"family": font.family, "size": font.size}
    if font.weight is not None:
        d["weight"] = font.weight
    if font.italic:
        d["italic"] = True
    if font.axes:
        d["axes"] = dict(font.axes)
    return d
