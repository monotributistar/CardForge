# CardForge — Roadmap

> Version: 0.1.0  
> Last updated: 2026-06-26

## Version Overview

| Version | Theme | Status |
|---------|-------|--------|
| v0.1 | **MVP: Business Card** | 🔨 In Design |
| v0.2 | **3MF + Templates** | 📋 Planned |
| v0.3 | **CLI + Multi-Type** | 📋 Planned |
| v0.4 | **Visual Editor** | 💡 Future |
| v1.0 | **Plugin Ecosystem** | 💡 Future |

---

## v0.1 — MVP: Business Card Generator

**Goal:** Working end-to-end pipeline from JSON config to printable STL.

### Deliverables

- [x] Repository structure and pyproject.toml
- [x] Architecture documentation (ARCHITECTURE.md)
- [x] Component contracts (COMPONENTS.md)
- [x] Pipeline documentation (PIPELINE.md)
- [x] Printing guidelines (PRINTING_GUIDELINES.md)
- [x] Example config (business_card_basic.json)
- [ ] Python package skeleton (src/cardforge/)
- [ ] Config loader + validator
- [ ] Template variable resolver
- [ ] QR code generator (SVG output)
- [ ] Pattern generator (text-repeat)
- [ ] OpenSCAD code generator (config → SCAD)
- [ ] OpenSCAD modules (base, rounded_rect, text_layer, qr_layer, pattern_layer, relief, color_layers)
- [ ] OpenSCAD CLI integration
- [ ] STL export (single file)
- [ ] STL export (color-separated)
- [ ] SVG preview generation
- [ ] PNG preview generation
- [ ] Build script (scripts/build.py)
- [ ] End-to-end integration test
- [ ] README with quick start

### Scope Boundaries

**In scope:**
- Business card with front and back faces
- Rounded rectangle base shape
- Text blocks (emboss/deboss)
- QR codes from vCard data (emboss)
- Simple text-repeat pattern (deboss)
- Logo from SVG file (emboss)
- Frame/border
- Corner radius
- Multi-color STL export
- SVG preview

**Out of scope (deferred):**
- Other object types (badges, labels, tags)
- 3MF export
- Advanced patterns (grid, hex, stripes)
- Hueforge integration
- Multiple templates
- Visual editor
- Font subsetting/embedding
- Slicer integration

### Implementation Plan

```
Phase 1: Foundation (Python)
  ├── Task 1.1: Config loader (JSON → dict)
  ├── Task 1.2: Config validator (schema + rules)
  ├── Task 1.3: Variable resolver ({{var}} substitution)
  └── Task 1.4: Pipeline orchestrator (stage runner)

Phase 2: Assets (Python)
  ├── Task 2.1: QR code generator (qrcode → SVG)
  ├── Task 2.2: Pattern generator (text-repeat → SVG)
  └── Task 2.3: SVG utilities (clean, validate, measure)

Phase 3: Geometry (OpenSCAD)
  ├── Task 3.1: Base shape module (rounded_rect.scad)
  ├── Task 3.2: Relief module (emboss, deboss, flush, cut)
  ├── Task 3.3: Text layer module
  ├── Task 3.4: QR layer module (SVG import + extrude)
  ├── Task 3.5: Pattern layer module
  ├── Task 3.6: Logo layer module
  ├── Task 3.7: Frame layer module
  ├── Task 3.8: Corner decoration module
  ├── Task 3.9: Color layer management (material separation)
  └── Task 3.10: SCAD generator (Python → OpenSCAD code)

Phase 4: Integration (Python + OpenSCAD)
  ├── Task 4.1: OpenSCAD CLI wrapper
  ├── Task 4.2: STL exporter (single + color-separated)
  ├── Task 4.3: Preview generator (SVG + PNG)
  ├── Task 4.4: Build script (scripts/build.py)
  └── Task 4.5: End-to-end test (config → STL → verify)

Phase 5: Polish
  ├── Task 5.1: README with quick start
  ├── Task 5.2: Example configs (basic + pattern)
  ├── Task 5.3: Test suite
  └── Task 5.4: Documentation review pass
```

---

## v0.2 — 3MF Export + Templates

**Goal:** Production-quality output with 3MF support and reusable templates.

### Deliverables

- 3MF export with multi-material metadata
- Template system (reusable config fragments)
- Additional object type: `event-badge`
- Advanced patterns: grid, hex, stripes
- Hueforge zone support (image → height map)
- Font embedding (bundle fonts with project)
- CLI commands: `cardforge init`, `cardforge build`, `cardforge list`
- Alignment features for glued multi-part prints

### Implementation Notes

- 3MF uses `py3mf` or direct ZIP+XML generation
- Templates work like Docker Compose extends: `"extends": "templates/standard-card.json"`
- Hueforge zone: accept PNG, convert to height map, integrate as feature type

---

## v0.3 — Full CLI + Multi-Type

**Goal:** Polished developer experience and support for all flat object types.

### Deliverables

- Full CLI: `cardforge init|validate|build|preview|export`
- Config schema published (JSON Schema)
- Additional types: `product-label`, `desk-plate`, `equipment-tag`, `keychain-card`, `qr-sign`, `brand-token`
- Config presets for common use cases
- Better error messages and validation
- Print settings embedded in 3MF
- Batch build (multiple configs at once)
- `--watch` mode for rapid iteration

---

## v0.4+ — Visual Editor & Ecosystem

**Status:** Documented for architecture awareness. Not scheduled.

### Ideas

- **Visual Web Editor:** Drag-and-drop feature placement, live preview
- **Plugin System:** Third-party feature types, exporters, pattern generators
- **Marketplace:** Share and discover config templates
- **Slicer Integration:** Direct "Open in PrusaSlicer/Bambu Studio" button
- **NFC Support:** Generate geometry for NFC tag cavities
- **STEP Export:** For CAD interoperability (advanced users)
- **DXF Export:** For laser cutting variants
- **Multi-language UI**

### Design Constraint

The architecture must support these without rewriting the core. Extension points are documented in [ARCHITECTURE.md](ARCHITECTURE.md#extension-points).

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-26 | JSON over YAML for configs | Schema validation, no dependency, strict syntax |
| 2026-06-26 | src layout for Python package | Avoids import shadowing, standard for modern projects |
| 2026-06-26 | uv for Python tooling | Fast, modern, single tool for venv+pip+pyproject |
| 2026-06-26 | OpenSCAD over Blender | Declarative, CLI-first, CSG-native, lighter |
| 2026-06-26 | SVG as intermediate format | 2D-native, OpenSCAD import, diffable |
| 2026-06-26 | STL first, 3MF later | STL universal; 3MF adds complexity for v0.2 |

---

## Contribution Guide (Future)

For now, this is a solo project. When the plugin system lands in v0.4, contribution guidelines will be added:

- How to add a new feature type
- How to add a new export format
- How to add a new object type
- Testing requirements
- Code style (ruff, mypy)
