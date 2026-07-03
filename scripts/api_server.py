#!/usr/bin/env python3
"""CardForge Core API Server — FastAPI entry point.

Usage:
    uv run python scripts/api_server.py
    uvicorn cardforge.api.server:app --reload --port 9000
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("cardforge.api.server:app", host="0.0.0.0", port=9000, reload=True)
