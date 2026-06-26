# CardForge — Pipeline

> Version: 0.1.0  
> Depends on: [ARCHITECTURE.md](ARCHITECTURE.md)

## Pipeline Overview

The CardForge pipeline transforms a JSON configuration into printable STL files through a sequence of well-defined stages. Each stage has explicit inputs, outputs, error handling, and dependencies.

```
[1] READ ──▶ [2] VALIDATE ──▶ [3] RESOLVE ──▶ [4] ASSETS ──▶ [5] SCAD ──▶ [6] RENDER ──▶ [7] EXPORT ──▶ [8] PREVIEW
```

## Stage 1: Read Config

**Module:** `src/cardforge/config/loader.py`  
**Function:** `load_config(path: str) -> dict`

### Input
- File path to JSON config (e.g., `configs/examples/business_card_basic.json`)

### Process
1. Open and read JSON file
2. Parse with `json.load()`
3. Return raw config dict

### Output
- Raw Python dict with all config fields

### Error Handling
- `FileNotFoundError` → "Config file not found: {path}"
- `json.JSONDecodeError` → "Invalid JSON in config: {error}"

### Dependencies
- None (first stage)

---

## Stage 2: Validate Config

**Module:** `src/cardforge/config/validator.py`  
**Function:** `validate_config(config: dict) -> dict`

### Input
- Raw config dict from Stage 1

### Process
1. Validate structure against JSON Schema
2. Type check all numeric fields
3. Range check dimensions (width, height, thickness, relief depths)
4. Reference check (template variables point to existing paths)
5. Asset check (referenced files exist on disk)
6. Consistency check (no contradictory constraints)
7. Return normalized config with defaults applied

### Output
- Validated and normalized config dict

### Validation Rules

| Check | Rule | Error Message |
|-------|------|---------------|
| Schema | Top-level keys present | "Missing required key: {key}" |
| Type | `width` is number | "object.width must be a number" |
| Range | `thickness` ≥ 1.0 | "object.thickness must be ≥ 1.0 mm" |
| Range | `thickness` ≤ 3.0 | "object.thickness must be ≤ 3.0 mm" |
| Range | `cornerRadius` ≤ min(width,height)/2 | "cornerRadius too large for dimensions" |
| Relief | `emboss.height` ≤ thickness/2 | "Emboss height exceeds half thickness" |
| Relief | `deboss.depth` ≤ thickness/2 | "Deboss depth exceeds half thickness" |
| Relief | `cut.depth` ≤ thickness | "Cut depth exceeds thickness" |
| Reference | Template var resolves | "Unresolved variable: {{owner.missing}}" |
| Asset | File exists | "Asset not found: {path}" |
| Consistency | No overlap conflicts | "Features overlap at z-index {n}" |

### Error Handling
- `ValidationError` with list of all validation failures (not just first)

### Dependencies
- Stage 1 (raw config)

---

## Stage 3: Resolve Variables

**Module:** `src/cardforge/config/resolver.py`  
**Function:** `resolve_config(config: dict) -> dict`

### Input
- Validated config dict from Stage 2

### Process
1. Walk entire config tree
2. Find all `{{path.to.var}}` patterns in string values
3. Resolve each against the config's own data
4. Produce a new config dict with all variables substituted
5. Validate that no unresolved variables remain

### Example

Input:
```json
{
  "owner": { "name": "Javier" },
  "lines": ["Hello {{owner.name}}"]
}
```

Output:
```json
{
  "owner": { "name": "Javier" },
  "lines": ["Hello Javier"]
}
```

### Resolution Rules
- Dot notation for nesting: `{{owner.contact.email}}`
- Variables can reference any path in the config
- Circular references detected and rejected
- Array indices NOT supported (use named keys only)

### Error Handling
- `UnresolvedVariableError` → "Cannot resolve {{path}}: not found in config"
- `CircularReferenceError` → "Circular reference detected: {{a}} → {{b}} → {{a}}"

### Dependencies
- Stage 2 (validated config)

---

## Stage 4: Generate Assets

**Orchestrator:** `src/cardforge/pipeline/stages.py`  
**Generators:** `src/cardforge/assets/qr_generator.py`, `src/cardforge/assets/pattern_generator.py`

### Input
- Resolved config dict from Stage 3

### Process

#### 4a. QR Code Generation
For each `qr` feature:
1. Extract QR data from `target` (e.g., vCard from owner info)
2. Generate QR matrix with specified error correction
3. Render as SVG with correct module size and quiet zone
4. Save to `assets/qr/{id}.svg`

#### 4b. Pattern Generation
For each `pattern` feature:
1. Determine pattern type (text-repeat, grid, hex, stripes, svg-file)
2. Generate repeating SVG pattern
3. Save to `assets/patterns/{id}.svg`

#### 4c. Logo Validation
For each `logo` feature:
1. Verify SVG file exists at specified path
2. Parse SVG to extract viewBox/dimensions
3. Validate SVG structure (no scripts, no external references)

### Output
- `assets/qr/{id}.svg` — Generated QR code SVGs
- `assets/patterns/{id}.svg` — Generated pattern SVGs

### Error Handling
- `QRGenerationError` → "Failed to generate QR: {reason}"
- `PatternGenerationError` → "Failed to generate pattern: {reason}"
- `InvalidSVGError` → "Invalid SVG file: {path}"

### Dependencies
- Stage 3 (resolved config)
- Python packages: `qrcode`, `svgwrite`, `Pillow`

---

## Stage 5: Generate OpenSCAD

**Module:** `src/cardforge/exporters/scad_generator.py`  
**Function:** `generate_scad(config: dict) -> str`

### Input
- Resolved config dict from Stage 3
- Generated asset paths from Stage 4

### Process
1. Create build directory: `exports/{project_name}/scad/`
2. Generate `config.scad` with all parameters:
   - Object dimensions (width, height, thickness, cornerRadius)
   - Layer height for preview accuracy
3. Generate `generated.scad` that:
   - Includes all OpenSCAD modules from `openscad/modules/`
   - Creates the base shape (rounded rectangle)
   - Iterates faces (front, back)
   - For each face, iterates features in zIndex order
   - For each feature, applies relief operation and material
   - Calls appropriate module (text_layer, qr_layer, pattern_layer, etc.)

### Generated SCAD Structure

```openscad
// Auto-generated by CardForge v0.1.0
// Do not edit manually

include <../config.scad>
include <../modules/base.scad>
include <../modules/text_layer.scad>
include <../modules/qr_layer.scad>
// ... other includes

// Generate front face
translate([0, 0, thickness/2]) {
    // Feature: background_monogram (z=0)
    pattern_layer(
        file = "assets/patterns/bg_monogram.svg",
        relief = "deboss",
        relief_depth = 0.2
    );
    // Feature: company_logo (z=1)
    logo_layer(
        file = "assets/logos/logo.svg",
        position = [42.5, 27],
        width = 24,
        relief = "emboss",
        relief_height = 0.5,
        material = "accent"
    );
}

// Generate back face
mirror([0, 0, 1]) {
    // ... back face features
}
```

### Output
- `exports/{project_name}/scad/config.scad`
- `exports/{project_name}/scad/generated.scad`

### Error Handling
- `SCADGenerationError` → "Failed to generate SCAD for feature {id}: {reason}"

### Dependencies
- Stage 4 (generated assets)
- OpenSCAD modules in `openscad/modules/`

---

## Stage 6: Render (OpenSCAD CLI)

**Module:** `src/cardforge/exporters/scad_generator.py`  
**Command:** `openscad -o output.stl input.scad`

### Input
- Generated SCAD files from Stage 5

### Process
1. Execute OpenSCAD CLI for single STL:
   ```
   openscad -o exports/{name}/stl/card_single.stl \
            exports/{name}/scad/generated.scad
   ```
2. Execute OpenSCAD CLI per material for color-separated STLs:
   ```
   openscad -D material="base" -o exports/{name}/stl/parts/01_base_black.stl ...
   openscad -D material="text" -o exports/{name}/stl/parts/02_text_white.stl ...
   openscad -D material="accent" -o exports/{name}/stl/parts/03_logo_gold.stl ...
   ```

### OpenSCAD Parameters
| Flag | Purpose |
|------|---------|
| `-o <path>` | Output file path |
| `-D var=value` | Set variable in SCAD |
| `--render` | Full render (not preview) for final output |
| `--export-format binstl` | Binary STL output |

### Output
- `exports/{name}/stl/card_single.stl` — Single combined STL
- `exports/{name}/stl/parts/01_base_{color}.stl` — Base material STL
- `exports/{name}/stl/parts/02_text_{color}.stl` — Text material STL
- ... (one STL per unique material used)

### Error Handling
- `OpenSCADNotFoundError` → "OpenSCAD CLI not found. Install with: brew install openscad"
- `OpenSCADRenderError` → "OpenSCAD render failed: {stderr}"

### Dependencies
- Stage 5 (generated SCAD)
- OpenSCAD CLI installed and in PATH

---

## Stage 7: Export Organization

**Module:** `src/cardforge/exporters/stl_exporter.py`

### Input
- Render outputs from Stage 6

### Process
1. Verify all STL files generated successfully
2. Calculate file sizes
3. Generate manifest.json with file inventory
4. Copy/rename files to final export structure

### Output Structure
```
exports/{project_name}/
├── manifest.json          # Build metadata and file inventory
├── preview/
│   ├── front.svg
│   ├── back.svg
│   ├── front.png
│   └── back.png
├── assets/
│   ├── qr_vcard.svg
│   └── pattern_bg.svg
├── scad/
│   ├── config.scad
│   └── generated.scad
├── stl/
│   ├── card_single.stl
│   └── parts/
│       ├── 01_base_black.stl
│       ├── 02_text_white.stl
│       └── 03_logo_gold.stl
└── 3mf/                   # v0.2
    └── card_multicolor.3mf
```

### Manifest Format
```json
{
  "project": "Javier_Business_Card",
  "version": "0.1.0",
  "timestamp": "2026-06-26T19:00:00Z",
  "config": "configs/examples/business_card_basic.json",
  "files": {
    "single_stl": "stl/card_single.stl",
    "parts": [
      { "material": "base", "color": "black", "file": "stl/parts/01_base_black.stl" },
      { "material": "text", "color": "white", "file": "stl/parts/02_text_white.stl" }
    ],
    "previews": ["preview/front.png", "preview/back.png"]
  }
}
```

### Dependencies
- Stage 6 (rendered STLs)

---

## Stage 8: Generate Previews

**Module:** `src/cardforge/exporters/preview.py`

### Input
- Resolved config from Stage 3
- Generated assets from Stage 4 (optional)

### Process
1. Generate 2D SVG preview of each face:
   - Draw face outline with dimensions
   - Render each feature in its position with correct size/rotation
   - Apply material colors
2. Rasterize SVG to PNG at 150 DPI:
   - Front face: light from above-left
   - Back face: light from above-right
3. Save to preview directory

### Output
- `exports/{name}/preview/front.svg` — Front face vector preview
- `exports/{name}/preview/back.svg` — Back face vector preview
- `exports/{name}/preview/front.png` — Front face raster preview
- `exports/{name}/preview/back.png` — Back face raster preview

### Dependencies
- Stage 3 (resolved config)
- Python packages: `svgwrite`, `Pillow`, `cairosvg` (optional, for SVG→PNG)

---

## Stage 9: 3MF Export (Future — v0.2)

Documented for architecture completeness. Not implemented in v0.1.

### Planned Behavior
1. Package all material-separated STLs into a single 3MF archive
2. Add per-material metadata (color, filament type)
3. Embed preview thumbnail
4. Add print settings hints (layer height, nozzle size)

### Target Library
- `lib3mf` Python bindings or `py3mf`

---

## Pipeline Execution Flow

```
cardforge build configs/examples/business_card_basic.json

  [1] READ ............... 0.002s  ✓
  [2] VALIDATE ........... 0.015s  ✓  (12 checks passed)
  [3] RESOLVE ............ 0.008s  ✓  (4 variables resolved)
  [4] ASSETS ............. 0.120s  ✓  (1 QR, 1 pattern)
  [5] SCAD ............... 0.045s  ✓  (generated.scad: 87 lines)
  [6] RENDER ............. 8.230s  ✓  (card_single.stl: 1.2 MB)
  [7] EXPORT ............. 0.030s  ✓  (3 STL files organized)
  [8] PREVIEW ............ 0.180s  ✓  (2 SVGs, 2 PNGs)

  Build complete: exports/Javier_Business_Card/
  Total time: 8.630s
```

## Error Recovery

If any stage fails:
1. Previous stage outputs are preserved (don't clean build directory on failure)
2. Error message includes stage number, description, and fix suggestion
3. User can re-run after fixing the issue — pipeline picks up where it left off
4. `--clean` flag forces full rebuild from scratch
