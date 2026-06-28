"""Geometry IR — abstract geometry nodes for renderer-independent representation.

CardForge's intermediate representation between the Domain Model and renderers.
Nodes form a tree: Document → Groups → Shapes → Transforms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Base Node ─────────────────────────────────────────────────────────────────

@dataclass
class GeometryNode(ABC):
    """Abstract base for all geometry nodes."""

    id: str = ""
    children: List[GeometryNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def accept(self, visitor: "GeometryVisitor") -> Any:
        """Accept a visitor (Visitor pattern)."""
        method_name = f"visit_{self.__class__.__name__}"
        visit_method = getattr(visitor, method_name, visitor.visit_default)
        return visit_method(self)

    def add_child(self, child: GeometryNode) -> None:
        self.children.append(child)


# ── Document ──────────────────────────────────────────────────────────────────

@dataclass
class DocumentNode(GeometryNode):
    """Root node of a geometry document."""

    name: str = "untitled"


# ── Group nodes ───────────────────────────────────────────────────────────────

@dataclass
class GroupNode(GeometryNode):
    """Logical grouping of children (no CSG operation)."""

    pass


@dataclass
class UnionNode(GeometryNode):
    """CSG union of all children."""

    pass


@dataclass
class DifferenceNode(GeometryNode):
    """CSG difference: first child minus all subsequent children."""

    pass


# ── Shape nodes (2D) ─────────────────────────────────────────────────────────

@dataclass
class RectangleNode(GeometryNode):
    """Axis-aligned rectangle (2D)."""

    width: float = 0.0
    height: float = 0.0
    center: bool = True


@dataclass
class RoundedRectangleNode(GeometryNode):
    """Rectangle with rounded corners (2D)."""

    width: float = 0.0
    height: float = 0.0
    radius: float = 0.0
    center: bool = True


@dataclass
class SVGNode(GeometryNode):
    """SVG file reference for import."""

    file_path: str = ""
    width: float = 0.0
    height: float = 0.0


@dataclass
class TextNode(GeometryNode):
    """Text element (2D)."""

    text: str = ""
    font: str = "sans-serif"
    font_size: float = 3.0
    font_weight: str = "bold"
    halign: str = "left"
    valign: str = "top"


# ── 3D / Transform nodes ─────────────────────────────────────────────────────

@dataclass
class ExtrudeNode(GeometryNode):
    """Linear extrusion of 2D children into 3D."""

    height: float = 1.0
    center: bool = False


@dataclass
class TranslateNode(GeometryNode):
    """Translation transform."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class RotateNode(GeometryNode):
    """Rotation transform (degrees)."""

    angle: float = 0.0
    axis: str = "z"  # x, y, z


@dataclass
class MirrorNode(GeometryNode):
    """Mirror transform."""

    axis: str = "z"  # x, y, z
