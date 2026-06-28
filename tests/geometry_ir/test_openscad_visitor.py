"""Tests for OpenSCADVisitor — Geometry IR → SCAD code."""

from cardforge.geometry_ir.nodes import (
    DocumentNode, UnionNode, RectangleNode, RoundedRectangleNode,
    ExtrudeNode, TranslateNode, TextNode, SVGNode, MirrorNode, GroupNode,
)
from cardforge.geometry_ir.openscad_visitor import OpenSCADVisitor


class TestOpenSCADVisitor:
    def test_renders_document(self):
        doc = DocumentNode(id="test", name="Test")
        visitor = OpenSCADVisitor()
        scad = visitor.render(doc)
        assert "CardForge" in scad
        assert "include" in scad
        assert "main.scad" in scad

    def test_renders_extruded_rounded_rect(self):
        rect = RoundedRectangleNode(id="base", width=85, height=54, radius=4)
        extrude = ExtrudeNode(id="base_extrude", height=1.8, children=[rect])
        union = UnionNode(id="body", children=[extrude])
        doc = DocumentNode(id="test", name="Test", children=[union])

        visitor = OpenSCADVisitor()
        scad = visitor.render(doc)
        assert "rounded_rect_2d" in scad
        assert "linear_extrude" in scad

    def test_renders_text_node(self):
        text = TextNode(id="t1", text="Hello", font="Arial", font_size=3.5)
        extrude = ExtrudeNode(id="te1", height=0.4, children=[text])
        trans = TranslateNode(id="tt1", x=10, y=20, z=1.8, children=[extrude])
        union = UnionNode(id="body", children=[trans])
        doc = DocumentNode(id="test", name="Test", children=[union])

        visitor = OpenSCADVisitor()
        scad = visitor.render(doc)
        assert "text_emboss_layer" in scad
        assert "Hello" in scad

    def test_renders_translate(self):
        rect = RectangleNode(id="r1", width=10, height=10)
        trans = TranslateNode(id="t1", x=5, y=3, z=1.8, children=[rect])
        doc = DocumentNode(id="test", name="Test", children=[trans])

        visitor = OpenSCADVisitor()
        scad = visitor.render(doc)
        assert "translate([5, 3, 1.8])" in scad

    def test_renders_mirror(self):
        rect = RectangleNode(id="r1", width=10, height=10)
        mirror = MirrorNode(id="m1", axis="z", children=[rect])
        doc = DocumentNode(id="test", name="Test", children=[mirror])

        visitor = OpenSCADVisitor()
        scad = visitor.render(doc)
        assert "mirror([0, 0, 1])" in scad

    def test_renders_union(self):
        a = RectangleNode(id="a", width=10, height=10)
        b = RectangleNode(id="b", width=5, height=5)
        union = UnionNode(id="u1", children=[a, b])
        doc = DocumentNode(id="test", name="Test", children=[union])

        visitor = OpenSCADVisitor()
        scad = visitor.render(doc)
        assert "union()" in scad

    def test_renders_svg_node(self):
        svg = SVGNode(id="qr1", file_path="/path/qr.svg", width=24, height=24)
        extrude = ExtrudeNode(id="e1", height=0.4, children=[svg])
        trans = TranslateNode(id="t1", x=0, y=0, z=1.8, children=[extrude])
        doc = DocumentNode(id="test", name="Test", children=[trans])

        visitor = OpenSCADVisitor()
        scad = visitor.render(doc)
        assert "svg_emboss_layer" in scad
        assert "qr.svg" in scad

    def test_single_child_union_no_wrapper(self):
        """Union with single child shouldn't wrap in union()."""
        rect = RectangleNode(id="r1", width=10, height=10)
        union = UnionNode(id="u1", children=[rect])
        doc = DocumentNode(id="test", name="Test", children=[union])

        visitor = OpenSCADVisitor()
        scad = visitor.render(doc)
        assert "union()" not in scad  # Single child, no wrapper needed
