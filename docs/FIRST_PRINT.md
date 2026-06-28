# CardForge — Your First Printable Business Card

> Step-by-step guide to design, validate, and print your first CardForge card.

## 1. Open Studio

```bash
cd cardforge
pnpm studio:dev
```

Open http://localhost:5173

## 2. Choose a Template

Click one of the template buttons in the top bar:

- **Minimal** — white card, black text, clean
- **Luxury** — black card, gold accent, JR pattern
- **Tech** — dark card, neon green, Courier font

Or click **New Card** for a blank template.

## 3. Edit Your Information

In the **Variables** panel (left sidebar), change:
- `name` — your full name
- `title` — your job title
- `email` — your email address
- `website` — your website URL
- `phone` — your phone number

All `{{name}}` references update instantly across the card.

## 4. Edit Text & QR

Click any feature in the left tree:
- **front-name** — edit your name text
- **front-title** — edit your title text  
- **contact** — edit contact lines (name, title, email, website)
- **qr** — edit QR URL and size

Use the Inspector (right panel) to change font size, material, and position.

## 5. Move Elements

Click a feature on the canvas → blue bounding box appears → drag to reposition.

Position snaps to card bounds. Preview recompiles on release.

## 6. Change Theme & Relief

In the Inspector:
- **Theme buttons** — Minimal / Dark Luxury / Tech / Industrial
- **Relief presets** — Flat / Subtle / Standard / Strong

These change colors and emboss height instantly.

## 7. Check Manufacturing Score

The bottom panel shows your live score:

- **✅ 95-100** — Excellent, ready to print
- **⚠️ 80-94** — Good, minor warnings
- **❌ < 80** — Review issues before printing

Indicators show status of: Overall, QR, Text, Relief.

## 8. Publish

Click **Publish** → review the summary → **Publish Package**.

CardForge generates:
- `resolved.cardforge.json` — your resolved document
- `front.svg` / `back.svg` — preview images
- `manufacturing_report.json` / `.md` — manufacturability report
- `card_single.stl` — single STL for printing
- `01_base_pla.stl`, `02_text_pla.stl`, `03_accent_pla.stl` — color-separated STLs
- `README_PRINT.md` — print instructions

## 9. Open in Your Slicer

The package is slicer-agnostic. Works with:

### Bambu Studio / OrcaSlicer
1. Import all `stl/parts/*.stl` files
2. Select "Yes — these files are a single object with multiple parts"
3. Assign each part to a different filament

### PrusaSlicer
1. Import all STL files
2. Right-click → Split to parts
3. Assign extruders per part

### Cura
1. Import all STL files
2. Select all → Merge models
3. Use "Per Model Settings" for multi-color

## 10. Print Settings

```
Nozzle: 0.4 mm
Layer Height: 0.20 mm
Wall Count: 3
Top/Bottom Layers: 4
Infill: 15% grid
Brim: 2 mm
Material: PLA
Temperature: 200°C / 60°C bed
```

## 11. Print!

Your card is ready. The whole process from opening Studio to having a printable STL takes **under 5 minutes**.

## Need the CLI?

```bash
# Build everything from terminal
uv run python scripts/core_cli.py publish your-card.cardforge.json
```

---

*CardForge does not depend on any specific slicer or printer brand. Use whatever tool fits your workflow.*
