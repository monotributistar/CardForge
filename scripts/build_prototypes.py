#!/usr/bin/env python3
"""Build all prototype cards in one command."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cardforge.document.prototype import prototype_build


PROTOTYPES = [
    "examples/prototypes/card_minimal.cardforge.json",
    "examples/prototypes/card_dark_luxury.cardforge.json",
    "examples/prototypes/card_tech_pattern.cardforge.json",
]


def main():
    failed = []
    for proto in PROTOTYPES:
        path = PROJECT_ROOT / proto
        if not path.exists():
            print(f"SKIP: {proto} — not found")
            continue

        print(f"\n{'='*60}")
        print(f"Building: {proto}")
        print(f"{'='*60}")
        result = prototype_build(str(path), clean=True)

        if result != 0:
            failed.append(proto)
            print(f"\nFAILED: {proto}")
        else:
            print(f"\nOK: {proto}")

    print(f"\n{'='*60}")
    print(f"Results: {len(PROTOTYPES) - len(failed)}/{len(PROTOTYPES)} built successfully")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        return 1
    print("All prototypes built successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
