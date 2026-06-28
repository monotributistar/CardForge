# CardForge — Physical Prototype Checklist

Use this guide when printing CardForge prototype cards for physical validation.

## Before Printing

### Slicer Setup

```
Nozzle: 0.4 mm
Layer Height: 0.20 mm
Initial Layer Height: 0.20 mm
Line Width: 0.45 mm
Wall Count: 3
Top Layers: 4
Bottom Layers: 4
Infill: 15% grid or gyroid
Brim: 2 mm
Material: PLA
Temperature: 200°C nozzle / 60°C bed
Speed: 40 mm/s outer walls, 60 mm/s inner
```

### Multi-Color Setup

If printing color-separated STLs:

1. Import all `stl/parts/*.stl` files together in your slicer
2. Select "Yes" when asked if files are a single multi-part object
3. Assign filaments:
   - `01_base_*.stl` → Base color (black/white)
   - `02_text_*.stl` → Text color (contrasting)
   - `03_accent_*.stl` → Accent color (gold/neon)

### Orientation

- Print flat on the bed (face up)
- Face-up: emboss text faces upward, no supports needed
- Face-down: smoother surface but text may need supports (not recommended)

## After Printing — Visual Check

| Check | Good | Pass? |
|-------|------|-------|
| Card dimensions | ~85 × 54 mm | ☐ |
| Thickness | ~1.8 mm | ☐ |
| Corner radius | ~4 mm, smooth | ☐ |
| Surface finish | No artifacts | ☐ |

### Text Legibility

| Check | Minimum | Pass? |
|-------|---------|-------|
| Name readable | 4 mm font | ☐ |
| Title readable | 3 mm font | ☐ |
| Email readable | 3.2 mm font | ☐ |
| Numbers readable | 3 mm | ☐ |
| Bold vs Regular visible | — | ☐ |

### QR Code

| Check | Method | Pass? |
|-------|--------|-------|
| QR scans | Phone camera from 15 cm | ☐ |
| QR scans | Phone camera from 30 cm | ☐ |
| QR scans | In moderate light | ☐ |
| QR scans | At angle (~30°) | ☐ |
| QR visual quality | No merged modules | ☐ |

### Relief / Deboss

| Check | Expected | Pass? |
|-------|----------|-------|
| Emboss height feel | ~0.4 mm tactile | ☐ |
| Deboss depth visible | ~0.2 mm visible | ☐ |
| No over-extrusion on relief | Clean edges | ☐ |
| Pattern visibility | Subtle, visible at angle | ☐ |

### Multi-Color

| Check | Pass? |
|-------|-------|
| Colors aligned | ☐ |
| No color bleeding | ☐ |
| Accent contrasts well | ☐ |

## Measurements (Calibre)

| Measurement | Expected | Actual |
|-------------|----------|--------|
| Width | 85.0 mm | |
| Height | 54.0 mm | |
| Thickness | 1.8 mm | |
| Corner radius | 4.0 mm | |
| Emboss height | 0.4 mm | |
| QR size | 24.0 mm | |

## Issues Found

| Issue | Prototype | Severity | Notes |
|-------|-----------|----------|-------|
| | | | |
| | | | |

## Improvements for Next Iteration

1.
2.
3.

## Notes

- Date printed:
- Printer:
- Filament brand/type:
- Total print time:
- Ambient temperature:
