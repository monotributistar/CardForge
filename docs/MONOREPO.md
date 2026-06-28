# CardForge — Monorepo Architecture

> Status: Foundation

## Philosophy

CardForge is a monorepo by design during active development. Keeping Core, Studio, Components, and Docs together enables:
- Coordinated refactors across layers
- Single test suite
- No versioning friction while the product matures
- Fast iteration on the prototype loop

The monorepo will eventually split when Studio reaches production stability.

## Structure

```
cardforge/                         # Root
├── package.json                   # Workspace root (pnpm)
├── pnpm-workspace.yaml            # Workspace definition
├── pyproject.toml                 # Python core (uv)
├── README.md                      # Project overview
│
├── apps/
│   └── studio/                    # CardForge Studio — visual IDE
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── index.html
│       └── src/
│           ├── main.tsx
│           ├── App.tsx
│           └── components/
│
├── packages/
│   ├── components/                # Reusable UI components (future)
│   │   └── README.md
│   └── schemas/                   # JSON Schema definitions
│       ├── cardforge.document.schema.json
│       └── cardforge.legacy.schema.json
│
├── src/cardforge/                 # Python Core (headless compiler)
├── openscad/                      # OpenSCAD modules
├── tests/                         # Python test suite (462 tests)
├── scripts/                       # Build scripts
├── examples/                      # Prototype documents
├── docs/                          # All documentation
└── exports/                       # Build outputs (gitignored)
```

## What Lives Where

### Root — Python Core
- **Path:** `src/cardforge/`, `tests/`, `scripts/`
- **Tool:** `uv` (Python), `pytest`
- **Commands:** `uv run pytest tests/`, `uv run python scripts/build.py`
- **Status:** Stable, 462 tests, feature-complete for v0.1

### apps/studio — Visual IDE
- **Path:** `apps/studio/`
- **Stack:** Vite + React 18 + TypeScript
- **Commands:** `pnpm studio:dev`, `pnpm studio:build`
- **Status:** Foundation — layout and static preview only

### packages/components — Shared UI (Future)
- **Path:** `packages/components/`
- **Purpose:** Reusable React components for Studio and future tools
- **Status:** Placeholder

### packages/schemas — JSON Schemas (Future)
- **Path:** `packages/schemas/`
- **Purpose:** Formal JSON Schema definitions for `.cardforge.json`
- **Status:** Placeholder

## Commands

```bash
# Python Core
uv run pytest tests/ -v                    # Run all tests (462)
uv run python scripts/build.py ...          # Build a document
uv run python scripts/build_prototypes.py   # Build all prototypes

# Studio
pnpm install                                 # Install JS deps
pnpm studio:dev                              # Start dev server
pnpm studio:build                            # Production build

# Root convenience
pnpm core:test                               # Alias for pytest
pnpm core:prototype                          # Build all prototypes
```

## Migration Strategy

Phase 1 (current): Python core stays at root. Studio added as `apps/studio/`. No core files moved.

Phase 2 (future): If Studio grows significantly, move Python core to `packages/core/` with wrapper scripts at root. This preserves `uv run pytest` and `uv run python scripts/build.py` via the workspace root.

Phase 3 (future): Split into separate repos when both Core and Studio are stable and independently versioned.

## What's NOT in scope yet

- Moving Python core to `packages/core/`
- WebSocket / API bridge between Studio and Core
- Hot-reload preview from Core
- Shared component library
- CI/CD pipeline
- Docker images
