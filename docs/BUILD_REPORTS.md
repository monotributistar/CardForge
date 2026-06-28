# CardForge — Build Reports (Fase 7)

> Version: 0.1.0

## Overview

Phase 7 integrates the Manufacturing Analysis Engine into the build pipeline. Every build now produces a manufacturing report in JSON and Markdown formats, plus console output showing manufacturability status.

## Build Command

```bash
# Basic build with manufacturing analysis
uv run python scripts/build.py configs/examples/business_card_basic.json

# With STL export
uv run python scripts/build.py configs/examples/business_card_basic.json --stl --parts

# Report only (no STL)
uv run python scripts/build.py configs/examples/business_card_basic.json --report-only

# Use a different profile
uv run python scripts/build.py configs/examples/business_card_basic.json --profile sla

# Ignore manufacturing errors and export anyway
uv run python scripts/build.py configs/examples/business_card_basic.json --stl --ignore-manufacturing-errors
```

## Console Output

```
──────────────────────────────────────────────
Manufacturing Analysis
Profile: Generic FDM 0.4mm (PLA, 0.4mm)
Score: 95/100 — Excellent — ready to print
Status: Manufacturable

Warnings:
  - Emboss height 0.20mm below minimum 0.3mm

Suggestions:
  - Increase emboss to at least 0.3mm
──────────────────────────────────────────────
```

When errors are found:

```
Status: Not manufacturable
Build blocked before STL export.
Use --ignore-manufacturing-errors to override.
```

## Generated Reports

```
exports/<project>/reports/
├── manufacturing_report.json    # Machine-readable
└── manufacturing_report.md      # Human-readable
```

### JSON Format

```json
{
  "profile": { "process": "fdm", "nozzle": 0.4, ... },
  "score": 95,
  "score_label": "Excellent — ready to print",
  "is_manufacturable": true,
  "error_count": 0,
  "warning_count": 1,
  "issues": [
    {
      "code": "min_emboss",
      "severity": "warning",
      "message": "Emboss height 0.20mm below minimum 0.3mm",
      "suggestion": "Increase emboss to at least 0.3mm"
    }
  ],
  "metrics": { ... },
  "suggestions": [ ... ]
}
```

## Pipeline Flow

```
load → validate → resolve → domain → exports → assets → preview
  → geometry_ir → manufacturing → [scad → stl] → summary
```

The manufacturing stage runs after Geometry IR is built and before STL export. If the report has errors and `--ignore-manufacturing-errors` is not set, the pipeline stops and STL is not generated.

## Flags

| Flag | Effect |
|------|--------|
| `--profile <name>` | Select manufacturing profile (fdm-standard, fdm-fine, sla) |
| `--report-only` | Run analysis + preview, skip STL |
| `--ignore-manufacturing-errors` | Export STL even with manufacturing errors |
| `--stl` | Generate single STL |
| `--parts` | Generate per-material STLs |

## Scoring Rules

| Score | Label | Behavior |
|-------|-------|----------|
| 95+ | Excellent | No blocking |
| 80-94 | Good | Warnings shown, build continues |
| 60-79 | Fair | Warnings shown, build continues |
| 30-59 | Poor | Build **blocked** unless `--ignore-manufacturing-errors` |
| 0-29 | Not manufacturable | Build **blocked** unless `--ignore-manufacturing-errors` |

Warnings never block the build. Only ERROR and FATAL issues block STL export.

## Integration Points

The manufacturing report is available at multiple points:

- **Console**: always printed during build
- **JSON**: for CI/CD, automated checks, future API
- **Markdown**: for human review, documentation, sharing
- **Pipeline context**: accessible to downstream stages for conditional logic
