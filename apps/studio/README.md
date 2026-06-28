# CardForge Studio

Visual IDE for CardForge — preview and inspect manufacturing documents.

## Status

**Bridge v0** — loads Core-generated exports for read-only visualization. Editing not yet implemented.

## Quick Start

```bash
# 1. Generate exports from Core
cd ../..
uv run python scripts/build.py examples/prototypes/card_dark_luxury.cardforge.json --prototype

# 2. Start Studio
cd apps/studio
pnpm dev

# 3. Open http://localhost:5173
# 4. Click "Load Files" and select:
#    - exports/card-dark-luxury/document/resolved.cardforge.json
#    - exports/card-dark-luxury/preview/front.svg
#    - exports/card-dark-luxury/preview/back.svg
#    - exports/card-dark-luxury/reports/manufacturing_report.json
```

## Architecture

```
Core (Python)                    Studio (React)
─────────────                    ──────────────
build.py --prototype     →       Load Files button
  ↓                              ↓
exports/<project>/        →      FileReader API
  document/resolved.json   →      state/studioStore.tsx
  preview/front.svg        →      Canvas.tsx (dangerouslySetInnerHTML)
  reports/report.json      →      BottomPanel.tsx
```

## Components

- **TopBar** — "Load Files" button, project name
- **LeftPanel** — Feature tree from document, clickable to select
- **Canvas** — SVG preview with front/back toggle and zoom
- **RightPanel** — Feature properties (read-only) or document info
- **BottomPanel** — Manufacturing score, warnings, suggestions

## State

React Context via `studioStore.tsx`:

```
document: CardForgeDocument | null
frontSvg: string | null
backSvg: string | null
manufacturingReport: ManufacturingReport | null
selectedFeatureId: string | null
errors: string[]
```

## Limitations

- **SVG rendered via dangerouslySetInnerHTML** — will need sanitization
- **No editing** — features are read-only
- **No persistence** — state resets on page reload
- **File loading only** — no API or backend bridge
- **Zoom is CSS transform** — not true SVG zoom
- **No dark mode toggle** — always dark theme

## Next Steps

- Sanitize SVG before rendering
- Add feature editing (position, size, text)
- Hot-reload when exports directory changes
- Better zoom/pan on Canvas
- Export config persistence
