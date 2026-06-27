"""Export paths — manages the export directory structure."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExportPaths:
    """Organized paths for a CardForge build export."""

    root: Path
    assets_dir: Path
    preview_dir: Path
    scad_dir: Path
    stl_dir: Path
    stl_parts_dir: Path
    three_mf_dir: Path


def sanitize_project_name(name: str) -> str:
    """Convert a project name to a safe directory name."""
    # Replace spaces and special chars with underscores
    safe = re.sub(r"[^\w\-.]", "_", name)
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    # Remove leading/trailing underscores
    safe = safe.strip("_")
    if not safe:
        safe = "unnamed"
    return safe


def prepare_export_paths(
    project_name: str,
    base_dir: Path = Path("exports"),
) -> ExportPaths:
    """Create and return organized export paths for a project build.

    Args:
        project_name: Project name (will be sanitized for directory use).
        base_dir: Root directory for exports.

    Returns:
        ExportPaths with all directories created.
    """
    safe_name = sanitize_project_name(project_name)
    root = base_dir / safe_name

    paths = ExportPaths(
        root=root,
        assets_dir=root / "assets",
        preview_dir=root / "preview",
        scad_dir=root / "scad",
        stl_dir=root / "stl",
        stl_parts_dir=root / "stl" / "parts",
        three_mf_dir=root / "3mf",
    )

    # Create all directories
    for attr in [
        "assets_dir", "preview_dir", "scad_dir",
        "stl_dir", "stl_parts_dir", "three_mf_dir",
    ]:
        getattr(paths, attr).mkdir(parents=True, exist_ok=True)

    return paths
