"""Tests for Geometry IR nodes and visitor pattern."""

import pytest
from cardforge.geometry_ir.nodes import (
    DocumentNode, GroupNode, UnionNode, DifferenceNode,
    RectangleNode, RoundedRectangleNode, SVGNode, TextNode,
    ExtrudeNode, TranslateNode, MirrorNode, GeometryNode,
)
from cardforge.geometry_ir.visitor import GeometryVisitor


class TestGeometryNodes:
    def test_document_node(self):
        doc = DocumentNode(id="test", name="Test Card")
        assert doc.id == "test"
        assert doc.name == "Test Card"
        assert doc.children == []
        assert doc.metadata == {}

    def test_node_metadata(self):
        node = GroupNode(id="g1", metadata={"layer": "content", "material": "base"})
        assert node.metadata["layer"] == "content"
        assert node.metadata["material"] == "base"

    def test_add_child(self):
        parent = GroupNode(id="parent")
        child = RectangleNode(id="r1", width=10, height=20)
        parent.add_child(child)
        assert len(parent.children) == 1
        assert parent.children[0] is child

    def test_shape_nodes(self):
        rect = RectangleNode(id="r1", width=85, height=54, center=True)
        assert rect.width == 85
        assert rect.height == 54
        assert rect.center is True

        rrect = RoundedRectangleNode(id="rr1", width=85, height=54, radius=4)
        assert rrect.radius == 4

    def test_svg_node(self):
        svg = SVGNode(id="qr1", file_path="/path/to/qr.svg", width=24, height=24)
        assert svg.file_path == "/path/to/qr.svg"
        assert svg.width == 24

    def test_text_node(self):
        text = TextNode(id="t1", text="Hello", font="Arial", font_size=3.5,
                        font_weight="bold", halign="left", valign="top")
        assert text.text == "Hello"
        assert text.font_weight == "bold"
        assert text.halign == "left"

    def test_extrude_node(self):
        rect = RectangleNode(id="r1", width=10, height=10)
        extrude = ExtrudeNode(id="e1", height=1.8, children=[rect])
        assert extrude.height == 1.8
        assert len(extrude.children) == 1

    def test_translate_node(self):
        child = RectangleNode(id="r1", width=10, height=10)
        trans = TranslateNode(id="t1", x=5, y=10, z=1.8, children=[child])
        assert trans.x == 5
        assert trans.y == 10
        assert trans.z == 1.8

    def test_mirror_node(self):
        child = GroupNode(id="g1")
        mirror = MirrorNode(id="m1", axis="z", children=[child])
        assert mirror.axis == "z"

    def test_nested_tree(self):
        doc = DocumentNode(id="doc", name="Test")
        union = UnionNode(id="body")
        base = RoundedRectangleNode(id="base", width=85, height=54, radius=4)
        extrude = ExtrudeNode(id="base_extrude", height=1.8, children=[base])
        union.add_child(extrude)
        doc.add_child(union)
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], UnionNode)
        assert len(doc.children[0].children) == 1
        assert isinstance(doc.children[0].children[0], ExtrudeNode)

    def test_union_with_multiple_children(self):
        union = UnionNode(id="u1")
        union.add_child(RectangleNode(id="a", width=10, height=10))
        union.add_child(RectangleNode(id="b", width=5, height=5))
        assert len(union.children) == 2

    def test_difference_node(self):
        diff = DifferenceNode(id="d1")
        diff.add_child(RectangleNode(id="body", width=100, height=100))
        diff.add_child(RectangleNode(id="hole", width=10, height=10))
        assert len(diff.children) == 2


class CountingVisitor(GeometryVisitor):
    """Test visitor that counts node types."""
    def __init__(self):
        self.counts = {}

    def _count(self, name):
        self.counts[name] = self.counts.get(name, 0) + 1

    def visit_default(self, node):
        self._count(type(node).__name__)
        return super().visit_default(node)

    def visit_DocumentNode(self, node):
        self._count("DocumentNode")
        return super().visit_DocumentNode(node)

    def visit_GroupNode(self, node):
        self._count("GroupNode")
        return super().visit_GroupNode(node)

    def visit_MirrorNode(self, node):
        self._count("MirrorNode")
        return super().visit_MirrorNode(node)


class TestVisitorPattern:
    def test_accept_dispatches_to_visitor(self):
        node = RectangleNode(id="r1", width=10, height=10)
        visitor = CountingVisitor()
        node.accept(visitor)
        assert visitor.counts.get("RectangleNode", 0) >= 1

    def test_visitor_traverses_tree(self):
        doc = DocumentNode(id="doc")
        group = GroupNode(id="g1")
        group.add_child(RectangleNode(id="r1", width=10, height=10))
        group.add_child(TextNode(id="t1", text="Hi"))
        doc.add_child(group)

        visitor = CountingVisitor()
        doc.accept(visitor)
        assert visitor.counts.get("DocumentNode", 0) >= 1
        assert visitor.counts.get("GroupNode", 0) >= 1
        assert visitor.counts.get("RectangleNode", 0) >= 1
        assert visitor.counts.get("TextNode", 0) >= 1

    def test_default_visitor_handles_unknown(self):
        node = MirrorNode(id="m1")
        visitor = CountingVisitor()
        node.accept(visitor)
        assert visitor.counts.get("MirrorNode", 0) >= 1
