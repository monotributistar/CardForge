# CardForge

> Open Manufacturing Compiler for Flat Objects  
> tarjetas · credenciales · badges · etiquetas · placas · señalética

[![Tests](https://img.shields.io/badge/tests-462-green)](#)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![OpenSCAD](https://img.shields.io/badge/openscad-2021.01-yellow)](https://openscad.org)
[![TypeScript](https://img.shields.io/badge/typescript-5.5-blue)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## What is CardForge?

CardForge converts editable `.cardforge.json` documents into printable 3D objects. Write a config declaring what you want (text, QR, logo, pattern, colors, relief) and CardForge generates the STL — plus previews, manufacturing analysis, and print-ready instructions.

**First use case:** 3D-printed business cards with embossed text, functional QR codes, decorative patterns, and multiple colors.

**Designed to extend:** event badges, product labels, desk plates, keychain cards, QR signs — all from the same engine.

## Architecture

```
.cardforge.json → Core Compiler → STL + Previews + Reports
                      │
                      └── Geometry IR ──┬── OpenSCAD → STL
                                        ├── SVG → Preview
                                        └── Analyzer → Manufacturing Report

Studio (React) → static outputs (future: live API)
```

## Monorepo Structure

```
cardforge/
├── apps/studio/          # CardForge Studio — visual IDE (React + Vite)
├── src/cardforge/        # Python Core — headless compiler
├── openscad/             # OpenSCAD modules
├── packages/             # Shared components & schemas (future)
├── examples/             # Prototype documents
├── docs/                 # Full documentation
└── scripts/              # Build scripts
```

See [docs/MONOREPO.md](docs/MONOREPO.md) for details.

## Quick Start

### Core (Python)

```bash
# Install dependencies
uv sync --extra dev

# Run tests (462)
uv run pytest tests/ -v

# Build a prototype
uv run python scripts/build.py examples/prototypes/card_minimal.cardforge.json --prototype

# Build all prototypes
uv run python scripts/build_prototypes.py
```

### Studio (Web)

```bash
# Install JS dependencies
pnpm install

# Start dev server
pnpm studio:dev

# Production build
pnpm studio:build
```

## Status

- **Core:** Feature-complete for v0.1 — 462 tests, STL export, multi-color, manufacturing analysis
- **Studio:** Foundation — layout and static preview (editing not yet implemented)
- **Documentation:** [docs/](docs/) — architecture, domain model, pipeline, manufacturing, prototype loop

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Core Compiler | Python 3.11+ (uv) |
| Geometry Engine | OpenSCAD 2021.01 |
| Config Format | JSON + `.cardforge.json` documents |
| Studio Frontend | React 18 + TypeScript + Vite |
| Package Manager | pnpm (JS) + uv (Python) |
| Testing | pytest (462 tests) |

## Documentation

- [📐 Architecture](docs/ARCHITECTURE.md)
- [🧩 Domain Model](docs/DOMAIN_MODEL.md)
- [⚙️ Pipeline](docs/PIPELINE.md)
- [🖨️ Printing Guidelines](docs/PRINTING_GUIDELINES.md)
- [🔧 Manufacturing Engine](docs/MANUFACTURING_ENGINE.md)
- [📊 Build Reports](docs/BUILD_REPORTS.md)
- [🎨 SVG Visitor](docs/SVG_VISITOR.md)
- [🔄 Prototype Loop](docs/PROTOTYPE_LOOP.md)
- [📦 Monorepo](docs/MONOREPO.md)
- [🖼️ Geometry IR](docs/GEOMETRY_IR.md)
- [🗺️ Roadmap](docs/ROADMAP.md)
- [✅ Physical Checklist](docs/PHYSICAL_PROTOTYPE_CHECKLIST.md)

## License

MIT — Javier Rodriguez, 2026.
