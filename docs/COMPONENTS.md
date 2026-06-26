# CardForge — Component Contracts

> Version: 0.1.0  
> Depends on: [ARCHITECTURE.md](ARCHITECTURE.md)

## Overview

CardForge objects are built from composable components. Every component has a defined contract — inputs, outputs, and behavior. This document specifies those contracts.

## Component Hierarchy

```
FlatObject          ← abstract: defines dimensions, faces, manufacturing params
  ├─ Face           ← front/back surface of the object
  │   └─ Feature    ← any visual/structural element on a face
  └─ Frame          ← edge treatment (borders, guards)
```

## FlatObject Contract

The root object. All printable things extend this.

```json
{
  "object": {
    "width": 85.0,
    "height": 54.0,
    "thickness": 1.8,
    "cornerRadius": 4.0,
    "type": "business-card"
  },
  "manufacturing": {
    "process": "fdm",
    "nozzle": 0.4,
    "layerHeight": 0.2,
    "units": "mm"
  }
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `width` | number | yes | > 0, practical range: 20–200 mm |
| `height` | number | yes | > 0, practical range: 20–200 mm |
| `thickness` | number | yes | 1.0–3.0 mm for FDM cards |
| `cornerRadius` | number | no | 0 to min(width,height)/2, default: 0 |
| `type` | string | yes | Object type identifier |

## Face Contract

A face is one side of the object. A Card has `front` and `back`. Some objects may have only one face.

```json
{
  "faces": {
    "front": {
      "features": [...]
    },
    "back": {
      "features": [...]
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `features` | array | yes | Ordered list of Feature objects |

Features are rendered in array order (index 0 = bottom layer, last = top layer). Override with `zIndex`.

## Feature — Common Interface

Every feature, regardless of type, shares these fields:

```json
{
  "id": "unique_id",
  "type": "feature-type",
  "face": "front",
  "position": { "x": 10.0, "y": 15.0 },
  "size": { "width": 40.0, "height": 20.0 },
  "rotation": 0,
  "material": "text",
  "relief": {
    "mode": "emboss",
    "height": 0.4
  },
  "visibility": "visible",
  "zIndex": 1,
  "source": "shared_asset_ref"
}
```

### Common Fields Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | — | Unique within the face. Used for debugging and overrides. |
| `type` | string | yes | — | Feature type discriminator. |
| `face` | string | no | inherits | Which face this belongs to (front/back). |
| `position` | object | no | `{x:0, y:0}` | Origin point in mm from top-left corner of face. |
| `size` | object | no | type-dependent | Bounding box in mm. |
| `rotation` | number | no | 0 | Clockwise rotation in degrees around position origin. |
| `material` | string | no | `"base"` | Material key for multi-color export. |
| `relief` | object | no | `{mode:"flush"}` | Z-axis treatment. |
| `visibility` | string | no | `"visible"` | `visible` or `hidden`. |
| `zIndex` | number | no | auto | Explicit layer ordering. Higher = on top. |
| `source` | string | no | — | Reference to a named asset (QR, logo file, pattern). |

### Relief Contract

```json
{
  "mode": "emboss",
  "height": 0.4
}
```

```json
{
  "mode": "deboss",
  "depth": 0.2
}
```

```json
{
  "mode": "flush"
}
```

```json
{
  "mode": "cut",
  "depth": 1.8
}
```

| Mode | Param | Unit | Range | Z Effect |
|------|-------|------|-------|-----------|
| `emboss` | `height` | mm | 0.1–1.0 | +Z from face surface |
| `deboss` | `depth` | mm | 0.1–1.0 | −Z into face surface |
| `flush` | — | — | — | Coplanar with face |
| `cut` | `depth` | mm | 0.1–thickness | Through-cut (subtractive) |

**Validation rules:**
- `emboss` height + `deboss` depth must not exceed object thickness
- `cut` depth must be ≤ object thickness
- `flush` must have neither `height` nor `depth`

## Feature Types — Specific Contracts

### TextBlock

Renders one or more lines of text with configurable font and alignment.

```json
{
  "type": "text-block",
  "id": "contact_info",
  "position": { "x": 8, "y": 12 },
  "width": 40,
  "font": "Montserrat",
  "fontSize": 3.2,
  "fontStyle": "bold",
  "align": "left",
  "lineHeight": 1.4,
  "lines": [
    "Javier Rodriguez",
    "Frontend Developer",
    "javier@example.com"
  ],
  "material": "text",
  "relief": {
    "mode": "emboss",
    "height": 0.4
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `lines` | string[] | yes | — | Array of text lines. Supports `{{var}}` templates. |
| `font` | string | no | system default | Font family name. Must be available or bundled. |
| `fontSize` | number | yes | — | Font size in mm. |
| `fontStyle` | string | no | `"regular"` | `regular`, `bold`, `semibold`. Bold recommended for FDM. |
| `align` | string | no | `"left"` | `left`, `center`, `right`. |
| `lineHeight` | number | no | 1.2 | Line spacing multiplier. |
| `width` | number | no | face width | Text box width for alignment/wrapping. |

**FDM recommendations:**
- Minimum font size: 2.5 mm for uppercase, 3.0 mm for mixed case
- Prefer bold/semibold for readability
- Minimum stroke width: 0.6 mm for legible lines

### QRCode

Generates a QR code from data and renders it as a relief feature.

```json
{
  "type": "qr",
  "id": "vcard_qr",
  "qrType": "vcard",
  "target": "owner",
  "size": 24,
  "errorCorrection": "M",
  "quietZone": 2,
  "position": { "x": 56, "y": 15 },
  "material": "text",
  "relief": {
    "mode": "emboss",
    "height": 0.4
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `qrType` | string | yes | — | `vcard`, `url`, `text`, `wifi` |
| `target` | string | yes | — | Data source reference (e.g., `owner`, `website`) |
| `size` | number | yes | — | QR code size in mm (square) |
| `errorCorrection` | string | no | `"M"` | `L` (7%), `M` (15%), `Q` (25%), `H` (30%) |
| `quietZone` | number | no | 2 | White border around QR in mm |

**FDM recommendations:**
- Minimum QR size: 22 mm (20×20 modules at 0.6 mm/module)
- Recommended: 24–30 mm for reliable scanning
- Quiet zone: minimum 2 mm (4 modules at standard density)
- Use `emboss` relief for best contrast

### Pattern

Repeating decorative element across a face.

```json
{
  "type": "pattern",
  "id": "bg_monogram",
  "patternType": "text-repeat",
  "text": "JR",
  "spacing": 7,
  "rotation": -25,
  "material": "base",
  "relief": {
    "mode": "deboss",
    "depth": 0.2
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `patternType` | string | yes | — | `text-repeat`, `grid`, `hex`, `stripes`, `svg-file` |
| `text` | string | conditional | — | Text to repeat (for `text-repeat` type) |
| `spacing` | number | no | 10 | Center-to-center spacing in mm |
| `rotation` | number | no | 0 | Pattern rotation in degrees |
| `file` | string | conditional | — | SVG file path (for `svg-file` type) |

### Logo

Renders an SVG logo at a specific position and size.

```json
{
  "type": "logo",
  "id": "company_logo",
  "file": "assets/logos/logo.svg",
  "position": { "x": 42.5, "y": 27 },
  "size": { "width": 24 },
  "material": "accent",
  "relief": {
    "mode": "emboss",
    "height": 0.5
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | string | yes | — | Path to SVG file (relative to project root) |
| `size` | object | yes | — | `{width}` or `{width, height}` in mm. Aspect ratio preserved if only width given. |

**Constraints:**
- SVG must be valid (no external references, no scripts)
- Complex SVGs may need simplification for FDM
- Minimum feature size in logo: 0.6 mm for reliable print

### Frame

Border or edge treatment around the object.

```json
{
  "type": "frame",
  "id": "card_border",
  "frameStyle": "border",
  "width": 2,
  "inset": 0,
  "material": "accent",
  "relief": {
    "mode": "emboss",
    "height": 0.3
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `frameStyle` | string | no | `"border"` | `border`, `double`, `groove`, `bevel` |
| `width` | number | no | 1.5 | Frame width in mm |
| `inset` | number | no | 0 | Distance from edge in mm |

### CornerDecoration

Corner treatment applied to all four corners.

```json
{
  "type": "corner",
  "id": "rounded_corners",
  "style": "notch",
  "radius": 4
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `style` | string | no | `"round"` | `round`, `notch`, `chamfer`, `cutout` |
| `radius` | number | no | cornerRadius | Override corner radius for decoration in mm |

## Material System

Materials are referenced by key. The theme defines the mapping:

```json
{
  "theme": {
    "name": "dark-luxury",
    "baseColor": "black",
    "textColor": "white",
    "accentColor": "gold"
  }
}
```

**Standard material keys:**

| Key | Export Behavior | Typical Use |
|-----|----------------|-------------|
| `base` | Base STL (body) | Card structure, background |
| `text` | Separate STL | Text, QR codes |
| `accent` | Separate STL | Logos, frames, decorations |
| `frame` | Separate or accent STL | Borders, edges |

**Multi-color export:** Features with different material keys are exported as separate STL files. The slicer assigns different filaments to each.

## Template Variables

Configuration supports `{{path.to.value}}` template syntax for variable resolution:

```json
{
  "owner": {
    "name": "Javier Rodriguez",
    "email": "javier@example.com"
  },
  "faces": {
    "back": {
      "features": [{
        "type": "text-block",
        "lines": [
          "{{owner.name}}",
          "{{owner.email}}"
        ]
      }]
    }
  }
}
```

**Resolution rules:**
- `{{owner.name}}` resolves to `"Javier Rodriguez"`
- Nested paths supported: `{{owner.contact.email}}`
- Unresolved variables raise validation error
- Variables work in: `lines`, `qr.target`, `pattern.text`

## Validation Contract

All configs must pass validation before processing:

1. **Schema validation:** JSON structure matches expected schema
2. **Type validation:** Field types correct (number is number, string is string)
3. **Range validation:** Dimensions, relief heights within physical limits
4. **Reference validation:** Template variables resolve, asset files exist
5. **Consistency validation:** No contradictory constraints (e.g., emboss > thickness)
