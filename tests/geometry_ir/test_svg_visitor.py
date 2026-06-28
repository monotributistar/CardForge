"""Tests for SVGVisitor — renders GeometryDocument to SVG."""

import pytest
from cardforge.geometry_ir.svg_visitor import SVGVisitor, DEFAULT_COLORS
from cardforge.geometry_ir.nodes import (
    DocumentNode, GroupNode, UnionNode, DifferenceNode,
    RectangleNode, RoundedRectangleNode, SVGNode, TextNode,
    ExtrudeNode, TranslateNode, RotateNode, MirrorNode,
)


class TestSVGVisitor:
    def test_renders_empty_document(self):
        doc = DocumentNode(id="doc", name="Test")
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert "<svg" in svg
        assert "</svg>" in svg
        assert 'viewBox="0 0 85.0 54.0"' in svg

    def test_renders_rounded_rectangle(self):
        base = RoundedRectangleNode(id="card_base", width=85, height=54, radius=4)
        doc = DocumentNode(id="doc", name="Test", children=[base])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert "<rect" in svg
        assert 'rx="4"' in svg

    def test_renders_text_node(self):
        text = TextNode(id="t1", text="Hello", font="Arial", font_size=3.5,
                        font_weight="bold")
        doc = DocumentNode(id="doc", name="Test", children=[text])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert "<text" in svg
        assert "Hello</text>" in svg
        assert 'font-family="Arial"' in svg
        assert 'font-weight="bold"' in svg

    def test_renders_svg_node(self):
        svg_node = SVGNode(id="qr1", file_path="assets/qr_vcard_qr.svg", width=24, height=24)
        doc = DocumentNode(id="doc", name="Test", children=[svg_node])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert "<image" in svg
        assert 'href="../assets/qr_vcard_qr.svg"' in svg

    def test_renders_translate_node(self):
        rect = RectangleNode(id="r1", width=10, height=10)
        trans = TranslateNode(id="t1", x=5, y=10, z=1.8, children=[rect])
        doc = DocumentNode(id="doc", name="Test", children=[trans])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert 'transform="translate(' in svg

    def test_renders_rotate_node(self):
        rect = RectangleNode(id="r1", width=10, height=10)
        rot = RotateNode(id="rot1", angle=45, children=[rect])
        doc = DocumentNode(id="doc", name="Test", children=[rot])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert 'rotate(45)' in svg

    def test_renders_mirror_node(self):
        rect = RectangleNode(id="r1", width=10, height=10)
        mirror = MirrorNode(id="m1", axis="z", children=[rect])
        doc = DocumentNode(id="doc", name="Test", children=[mirror])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert 'scale(1, -1)' in svg

    def test_extrude_renders_child(self):
        rect = RectangleNode(id="r1", width=10, height=10, metadata={"material": "text"})
        extrude = ExtrudeNode(id="e1", height=1.8, children=[rect])
        doc = DocumentNode(id="doc", name="Test", children=[extrude])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert "<rect" in svg  # child rendered

    def test_material_color_applied(self):
        rect = RectangleNode(id="r1", width=10, height=10, metadata={"material": "accent"})
        doc = DocumentNode(id="doc", name="Test", children=[rect])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert '#ffd700' in svg  # accent = gold

    def test_difference_node_reduced_opacity(self):
        a = RectangleNode(id="body", width=100, height=100)
        b = RectangleNode(id="hole", width=10, height=10)
        diff = DifferenceNode(id="d1", children=[a, b])
        doc = DocumentNode(id="doc", name="Test", children=[diff])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert 'opacity="0.6"' in svg

    def test_face_filter_front_only(self):
        text = TextNode(id="t1", text="Front", metadata={"face": "front"})
        doc = DocumentNode(id="doc", name="Test", children=[text])
        visitor = SVGVisitor(face_id="front")
        svg = visitor.render(doc)
        assert "Front" in svg

    def test_face_filter_excludes_back(self):
        text = TextNode(id="t1", text="Back", metadata={"face": "back"})
        doc = DocumentNode(id="doc", name="Test", children=[text])
        visitor = SVGVisitor(face_id="front")
        svg = visitor.render(doc)
        assert "Back" not in svg

    def test_default_colors_have_expected_keys(self):
        assert "base" in DEFAULT_COLORS
        assert "text" in DEFAULT_COLORS
        assert "accent" in DEFAULT_COLORS
        assert DEFAULT_COLORS["base"] == "#1a1a1a"

    def test_svg_has_xmlns(self):
        doc = DocumentNode(id="doc", name="Test")
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_renders_nested_structure(self):
        rect = RectangleNode(id="r1", width=10, height=10, metadata={"material": "text"})
        extrude = ExtrudeNode(id="e1", height=0.4, children=[rect])
        trans = TranslateNode(id="t1", x=5, y=5, z=1.8, children=[extrude])
        doc = DocumentNode(id="doc", name="Test", children=[trans])
        visitor = SVGVisitor()
        svg = visitor.render(doc)
        assert "<rect" in svg
