#!/usr/bin/env python3
"""CardForge build script — thin wrapper over `cardforge build` (v2 pipeline)."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cardforge.cli import main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ("build", "validate"):
        sys.argv.insert(1, "build")  # `build.py doc.json` == `cardforge build doc.json`
    sys.exit(main())
