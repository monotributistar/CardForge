"""Renderer Protocol — defines the interface for geometry renderers."""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from cardforge.geometry_ir.nodes import DocumentNode


class GeometryRenderer(Protocol):
    """Protocol for geometry renderers.

    A renderer converts a GeometryDocument into an output format
    (SCAD, SVG, STL, Canvas commands, etc.).

    Example implementations:
        - OpenSCADRenderer → .scad text
        - SVGRenderer → .svg text
        - CanvasRenderer → drawing commands
        - ThreeJSRenderer → WebGL scene
    """

    def render(self, document: DocumentNode) -> str:
        """Render a geometry document to a string output."""
        ...
