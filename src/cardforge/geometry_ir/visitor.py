"""Geometry Visitor — abstract visitor for traversing geometry node trees."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from cardforge.geometry_ir.nodes import GeometryNode


class GeometryVisitor(ABC):
    """Abstract visitor for Geometry IR nodes.

    Subclasses override visit_<NodeType> methods for specific node types.
    Default traversal walks children in order.
    """

    def visit_default(self, node: GeometryNode) -> Any:
        """Fallback for nodes without a specific visitor method."""
        return self._visit_children(node)

    def visit_DocumentNode(self, node: GeometryNode) -> Any:
        return self._visit_children(node)

    def visit_GroupNode(self, node: GeometryNode) -> Any:
        return self._visit_children(node)

    def visit_UnionNode(self, node: GeometryNode) -> Any:
        return self._visit_children(node)

    def visit_DifferenceNode(self, node: GeometryNode) -> Any:
        return self._visit_children(node)

    def visit_ExtrudeNode(self, node: GeometryNode) -> Any:
        return self._visit_children(node)

    def visit_TranslateNode(self, node: GeometryNode) -> Any:
        return self._visit_children(node)

    def visit_RotateNode(self, node: GeometryNode) -> Any:
        return self._visit_children(node)

    def visit_MirrorNode(self, node: GeometryNode) -> Any:
        return self._visit_children(node)

    def _visit_children(self, node: GeometryNode) -> List[Any]:
        """Visit all children and return list of results."""
        return [child.accept(self) for child in node.children]
