"""OpenSCAD CLI wrapper — finds and runs the OpenSCAD executable."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OpenSCADResult:
    """Result of an OpenSCAD invocation."""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    output_file: Optional[Path] = None


class OpenSCADNotFoundError(Exception):
    """Raised when the OpenSCAD executable cannot be found."""
    pass


class OpenSCADError(Exception):
    """Raised when OpenSCAD execution fails."""
    pass


def find_openscad() -> str:
    """Find the OpenSCAD executable.

    Checks in order:
        1. OPENSCAD_BIN environment variable
        2. openscad on PATH
        3. Common macOS paths

    Returns:
        Path to the OpenSCAD executable.

    Raises:
        OpenSCADNotFoundError: If OpenSCAD is not found.
    """
    # 1. Environment variable
    env_bin = os.environ.get("OPENSCAD_BIN")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    # 2. PATH
    which = shutil.which("openscad")
    if which:
        return which

    # 3. macOS common paths
    mac_paths = [
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        "/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD",
    ]
    for p in mac_paths:
        if os.path.isfile(p):
            return p

    raise OpenSCADNotFoundError(
        "OpenSCAD executable not found. Install OpenSCAD or set OPENSCAD_BIN env var.\n"
        "  macOS: brew install --cask openscad\n"
        "  Then: export OPENSCAD_BIN=/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    )


def run_openscad(
    input_scad: Path,
    output_stl: Path,
    openscad_bin: Optional[str] = None,
    timeout: int = 120,
) -> OpenSCADResult:
    """Run OpenSCAD to render a .scad file to STL.

    Args:
        input_scad: Path to the .scad input file.
        output_stl: Path for the output .stl file.
        openscad_bin: Optional path to OpenSCAD executable.
        timeout: Maximum time in seconds.

    Returns:
        OpenSCADResult with success status and output.

    Raises:
        OpenSCADNotFoundError: If executable not found.
    """
    if openscad_bin is None:
        openscad_bin = find_openscad()

    output_stl.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        openscad_bin,
        "-o", str(output_stl),
        "--export-format", "binstl",
        str(input_scad),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = OpenSCADResult(
            success=proc.returncode == 0 and output_stl.exists(),
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            output_file=output_stl if output_stl.exists() else None,
        )
        return result
    except subprocess.TimeoutExpired:
        return OpenSCADResult(
            success=False,
            returncode=-1,
            stdout="",
            stderr=f"OpenSCAD timed out after {timeout}s",
        )
    except FileNotFoundError:
        raise OpenSCADNotFoundError(
            f"OpenSCAD executable not found: {openscad_bin}"
        )
