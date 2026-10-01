"""Where the project lives — one answer for the CLI, the API and the MCP server.

Three anchors used to coexist: the API derived a root from `__file__` (wrong
under a non-editable install, where it lands in site-packages' parent), the CLI
and pipeline used the current directory, and the font index used a
CWD-relative `assets/fonts`. This module is the single place that decides.
"""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """The CardForge project directory: examples/, assets/ and the default
    asset root for SVG references.

    Resolution order:
      1. `CARDFORGE_ROOT` in the environment, when set.
      2. The source checkout this module was imported from (editable install
         or `uv run` inside the repo), detected by `pyproject.toml` next to
         `src/cardforge`.
      3. The current working directory — the same anchor the CLI uses.
    """
    env = os.environ.get("CARDFORGE_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "cardforge").is_dir():
            return parent
    return Path.cwd()


def user_path(path: str | os.PathLike[str]) -> Path:
    """Resolve a caller-supplied path the way every CLI does: relative to the
    current working directory, never to the package's own location."""
    return Path(path).expanduser().resolve()
