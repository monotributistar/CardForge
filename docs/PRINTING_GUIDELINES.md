# CardForge — FDM Printing Guidelines

> Version: 0.1.0  
> Target: FDM printers with 0.4 mm nozzle

## Why These Guidelines Matter

CardForge generates geometry that must be physically printable. Every design decision — font sizes, relief heights, QR dimensions — is constrained by what an FDM printer with a standard 0.4 mm nozzle can actually produce.

These guidelines are baked into the validation stage. Configs that violate them will fail validation with a clear message.

## Nozzle 0.4 mm — The Reference Standard

The 0.4 mm brass nozzle is the default on virtually every consumer FDM printer (Prusa, Bambu, Creality, Voron). All CardForge defaults and validations assume this setup.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Nozzle diameter | 0.4 mm | Industry standard |
| Minimum extrusion width | 0.4 mm | Equal to nozzle diameter |
| Recommended extrusion width | 0.45 mm | 112% of nozzle for better adhesion |
| Minimum layer height | 0.08 mm | Practical lower bound for 0.4 mm nozzle |
| Standard layer height | 0.2 mm | Good balance of speed and detail |
| Maximum layer height | 0.28 mm | 70% of nozzle diameter |

## Minimum Detail Constraints

### Line Width

The printer cannot produce features narrower than the extrusion width.

| Feature | Minimum | Recommended | Reason |
|---------|---------|-------------|--------|
| Raised line (emboss) | 0.6 mm | 0.8 mm+ | Thin extrusions curl or detach |
| Recessed line (deboss) | 0.4 mm | 0.6 mm+ | Recessed features are more forgiving |
| Gap between features | 0.8 mm | 1.2 mm+ | Avoids features merging |
| Wall thickness (frame) | 0.8 mm | 1.2 mm+ | Prevents fragile edges |

### Text Legibility

Text is the most demanding feature for FDM. Small text becomes illegible fast.

| Text Type | Minimum Font Size | Recommended |
|-----------|-------------------|-------------|
| Uppercase only | 2.5 mm | 3.5 mm+ |
| Mixed case | 3.0 mm | 4.0 mm+ |
| Numbers | 2.5 mm | 3.0 mm+ |
| Symbols (@, ., -) | 3.5 mm | 4.5 mm+ |

**Font style matters:**
- **Bold/Semibold:** Always preferred. Thicker strokes = more material = better legibility.
- **Regular:** Acceptable above 4.0 mm.
- **Light/Thin:** Avoid entirely. Too fragile.
- **Serif:** Avoid below 4.0 mm. Serifs are thinner than strokes and disappear.
- **Sans-serif:** Preferred. Cleaner at small sizes.

**Recommended fonts for FDM:**
- Montserrat Bold/Semibold
- Inter Bold/Semibold
- Roboto Bold
- Helvetica Bold
- Arial Bold

## QR Code Specifications

QR codes are grids of black/white modules. For FDM, each module becomes a raised or recessed square.

### Size Requirements

| Parameter | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| QR overall size | 22 mm | 25–30 mm | Smaller = modules too fine to print |
| Module size | 0.6 mm | 0.8 mm+ | Each QR square |
| Quiet zone | 2 mm | 3 mm | White border around QR |

### QR Size vs Data Density

For a standard vCard QR (Version 4, ~50 characters):

| QR Size (mm) | Modules | Module Size (mm) | Printable? |
|-------------|---------|------------------|------------|
| 20 | 33×33 | 0.61 | Borderline — may not scan |
| 22 | 33×33 | 0.67 | OK — prints but test after |
| 24 | 33×33 | 0.73 | Good — reliable |
| 28 | 33×33 | 0.85 | Excellent |

For longer URLs (Version 6, ~100 characters):

| QR Size (mm) | Modules | Module Size (mm) | Printable? |
|-------------|---------|------------------|------------|
| 24 | 41×41 | 0.59 | Risky |
| 28 | 41×41 | 0.68 | OK |
| 32 | 41×41 | 0.78 | Good |

### Relief Mode for QR Codes

| Mode | Contrast | Scannability | Notes |
|------|----------|-------------|-------|
| `emboss` | Best | Excellent | Raised modules catch light, easy to scan |
| `deboss` | Good | Good | Recessed modules; depends on lighting |
| `flush` | Depends on color | Variable | Only works with stark color difference |

**Recommendation:** Always use `emboss` for QR codes. The height difference creates a natural shadow that phone cameras read easily.

## Relief Dimensions

### Emboss (Raised)

```
Base surface ─────────────────────────
                ╱ ╲    ← raised feature (height: 0.4 mm)
```

| Height | Printability | Visual Impact | Notes |
|--------|-------------|---------------|-------|
| 0.2 mm | Excellent | Subtle | 1 layer at 0.2 mm LH |
| 0.3 mm | Excellent | Visible | 1-2 layers |
| 0.4 mm | Good | Clear | 2 layers — good default |
| 0.5 mm | Good | Strong | 2-3 layers |
| 0.6 mm | Acceptable | Bold | 3 layers — max recommended |
| 0.8 mm+ | Risky | Aggressive | May need supports or cause overhangs |

### Deboss (Recessed)

```
Base surface ───╲  ╱───    ← recessed feature (depth: 0.2 mm)
                 ╲╱
```

| Depth | Printability | Visual Impact | Notes |
|-------|-------------|---------------|-------|
| 0.1 mm | Excellent | Very subtle | 0.5 layers — barely visible |
| 0.15 mm | Excellent | Subtle | Good for watermarks |
| 0.2 mm | Good | Visible | 1 layer — good default |
| 0.3 mm | Good | Clear | 1-2 layers |
| 0.4 mm+ | Acceptable | Strong | 2+ layers — affects structural integrity |

### Flush (Coplanar)

Features at the same Z level as the surface. Relies entirely on color difference for visibility.

- Only works with multi-material printing (MMU/AMS) or filament swaps
- No physical texture — purely visual
- Best for large areas of solid color

### Cut (Through)

Features that cut through the card. Only applicable to thin sections or frames.

- `cut.depth` must be ≤ `object.thickness`
- Full cuts create holes — consider structural integrity
- Edge quality depends on printer calibration

## Card Dimensions

### Thickness

| Thickness | Layers at 0.2mm | Flexibility | Durability |
|-----------|-----------------|-------------|------------|
| 1.2 mm | 6 | Very flexible | Fragile |
| 1.6 mm | 8 | Flexible | Acceptable |
| 1.8 mm | 9 | Slightly flexible | Good |
| 2.0 mm | 10 | Stiff | Good — recommended |
| 2.2 mm | 11 | Very stiff | Excellent |
| 2.5 mm+ | 12+ | Rigid | Overkill |

**Recommendation:** 1.8–2.0 mm. Matches standard credit card feel, prints in ~10 layers at 0.2 mm.

### Standard Card Sizes

| Type | Width × Height (mm) | Standard |
|------|---------------------|----------|
| Business card (US) | 88.9 × 50.8 | 3.5 × 2.0 in |
| Business card (EU) | 85 × 55 | ISO 7810 ID-1 |
| Credit card | 85.6 × 53.98 | ISO 7810 ID-1 |
| CardForge default | 85 × 54 | Slightly simplified ISO |

## Multi-Color Printing Strategy

CardForge separates geometry by material so multi-color prints work cleanly.

### Method 1: Manual Filament Swap (Single Extruder)

1. Print base STL (e.g., black)
2. Pause at layer where color changes
3. Swap filament to text color (e.g., white)
4. Resume print
5. Repeat for accent color

**Requirements:**
- Color transitions happen at clean Z heights (whole layer boundaries)
- CardForge outputs a "pause at layer N" instruction in manifest.json

### Method 2: Multi-Material Unit (MMU/AMS)

1. Load all filaments
2. Slice all STL parts together as a single multi-body print
3. Assign each body to a different extruder/filament
4. Printer handles swaps automatically

**CardForge output:** One STL file per material, designed to be aligned in the slicer as a multi-body assembly.

### Method 3: Separate Parts + Glue

1. Print each material STL separately
2. Align and glue/insert

**CardForge output:** Color-separated STLs with alignment features (future v0.2).

## Layer Height Trade-offs

| Layer Height | Detail | Speed | Surface Finish |
|-------------|--------|-------|----------------|
| 0.08 mm | Excellent | Very slow | Glass-like |
| 0.12 mm | Great | Slow | Smooth |
| 0.16 mm | Good | Moderate | Fine lines visible |
| 0.20 mm | Acceptable | Fast | Visible layers — **CardForge default** |
| 0.28 mm | Low | Very fast | Rough — not recommended for cards |

**Recommendation:** 0.16–0.20 mm. Cards are small objects where layer lines are visible up close. 0.20 mm is the pragmatic default; 0.16 mm for high-quality cards.

## Print Orientation

Cards should be printed flat on the bed:

- **Face down:** Text/features on bottom → smooth bed surface, but supports needed for overhangs
- **Face up:** Text/features on top → visible layer lines on text, no supports needed
- **Vertical:** Edge-on → terrible idea, avoid

**Recommendation:** Face up. The slight layer texture on top is acceptable; no supports needed for emboss features. For "show quality" cards, print face down on a textured/smooth PEI sheet.

## Material Recommendations

| Material | Pros | Cons | Best For |
|----------|------|------|----------|
| PLA | Easy, cheap, good detail | Brittle, low temp resistance | Prototypes, decorative cards |
| PLA+ / Tough PLA | Stronger, slight flex | Slightly more expensive | Everyday cards |
| PETG | Durable, flex, temperature resistant | Stringing, harder to print | Cards that need to last |
| PLA Silk | Beautiful finish | Weaker layer adhesion | Show pieces, gifts |
| PLA Matte | Hides layer lines | Slightly weaker | Professional-looking cards |

## Common Print Failures and Prevention

| Failure | Cause | Prevention |
|---------|-------|------------|
| Text unreadable | Font too small/thin | Use ≥ 3.0 mm bold fonts |
| QR doesn't scan | QR too small, modules merge | Use ≥ 24 mm QR with `emboss` |
| Features detach | Relief too tall, poor adhesion | Stay ≤ 0.6 mm emboss height |
| Color bleed | Color transition at wrong Z | Export color-separated STLs |
| Warped corners | Bed adhesion, cooling | Use brim (2-3 mm), enable part cooling |
| Stringing between text | Retraction settings | PETG: increase retraction; PLA: lower temp |
| Thin walls break | Frame width too small | Minimum 0.8 mm frame width |

## Slicer Settings (Starting Point)

These are the settings CardForge assumes for validation. Adjust to your printer.

```
Nozzle: 0.4 mm
Layer Height: 0.20 mm
Initial Layer Height: 0.20 mm
Line Width: 0.45 mm
Wall Count: 3 (for card durability)
Top/Bottom Layers: 4
Infill: 15% grid or gyroid
Material: PLA
Temperature: 200°C nozzle / 60°C bed
Speed: 40 mm/s (outer walls), 60 mm/s (inner)
Retraction: 0.8 mm @ 40 mm/s (direct drive)
Brim: 2 mm (cards are small, brim helps adhesion)
```

## Validation Checklist

Before printing, CardForge validates:

- [ ] Card dimensions within printable range (20–200 mm)
- [ ] Card thickness 1.0–3.0 mm
- [ ] All text font sizes ≥ minimum for chosen font style
- [ ] QR codes ≥ 22 mm with `emboss` relief
- [ ] QR quiet zone ≥ 2 mm
- [ ] Emboss heights ≤ 0.6 mm
- [ ] Deboss depths ≤ 0.3 mm
- [ ] Cut depths ≤ card thickness
- [ ] Frame widths ≥ 0.8 mm
- [ ] No feature overlap conflicts
- [ ] All referenced asset files exist
