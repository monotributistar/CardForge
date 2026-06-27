"""STL parts exporter — exports per-material STL files."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from cardforge.domain.card import Card
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.export.paths import ExportPaths
from cardforge.export.openscad_cli import run_openscad, OpenSCADResult, OpenSCADNotFoundError


@dataclass
class OpenSCADJob:
    """A single OpenSCAD render job."""
    scad_path: Path
    stl_path: Path
    material_id: str


def run_openscad_many(
    jobs: List[OpenSCADJob],
    openscad_bin: Optional[str] = None,
    timeout: int = 120,
    include_dirs: Optional[list[Path]] = None,
) -> List[OpenSCADResult]:
    """Run OpenSCAD for multiple jobs sequentially.

    Args:
        jobs: List of render jobs.
        openscad_bin: Optional path to OpenSCAD executable.
        timeout: Timeout per job in seconds.
        include_dirs: Optional list of directories for OpenSCAD include path.

    Returns:
        List of results, one per job (same order).
    """
    results = []
    for job in jobs:
        try:
            result = run_openscad(
                job.scad_path, job.stl_path,
                openscad_bin=openscad_bin, timeout=timeout,
                include_dirs=include_dirs,
            )
        except OpenSCADNotFoundError as e:
            result = OpenSCADResult(
                success=False, returncode=-1,
                stdout="", stderr=str(e),
            )
        results.append(result)
    return results


def export_material_stls(
    card: Card,
    material_scad_paths: Dict[str, Path],
    export_paths: ExportPaths,
    openscad_bin: Optional[str] = None,
    include_dirs: Optional[list[Path]] = None,
) -> List[Path]:
    """Export per-material STL files from generated SCAD files.

    Args:
        card: Card domain object (for material color names).
        material_scad_paths: Dict of material_id → .scad path.
        export_paths: Export directory structure.
        openscad_bin: Optional path to OpenSCAD executable.
        include_dirs: Optional OpenSCAD include directories.

    Returns:
        List of generated STL paths.

    Raises:
        OpenSCADNotFoundError: If OpenSCAD is not available.
    """
    from cardforge.scad.material_groups import get_material_filename

    stl_paths = []
    jobs = []

    for i, (mat_id, scad_path) in enumerate(sorted(material_scad_paths.items()), 1):
        mat = card.materials.get(mat_id)
        color_name = mat.name.split()[-1] if mat and mat.name else ""
        stl_name = get_material_filename(mat_id, color_name, i)
        stl_path = export_paths.stl_parts_dir / stl_name

        jobs.append(OpenSCADJob(
            scad_path=scad_path,
            stl_path=stl_path,
            material_id=mat_id,
        ))

    results = run_openscad_many(jobs, openscad_bin=openscad_bin, include_dirs=include_dirs)

    for job, result in zip(jobs, results):
        if result.success and result.output_file:
            stl_paths.append(result.output_file)

    return stl_paths
