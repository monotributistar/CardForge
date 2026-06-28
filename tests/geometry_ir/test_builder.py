"""Tests for GeometryBuilder — Card → GeometryDocument conversion."""

from cardforge.geometry_ir.builder import GeometryBuilder
from cardforge.geometry_ir.nodes import (
    DocumentNode, UnionNode, ExtrudeNode, TranslateNode, SVGNode,
    TextNode, MirrorNode, GroupNode,
)
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.export.paths import prepare_export_paths
from cardforge.domain.card import Card
from cardforge.domain.face import Face
from cardforge.domain.layer import Layer
from cardforge.domain.feature import TextBlockFeature, QRCodeFeature, PatternFeature
from cardforge.domain.geometry import Position, Size, ReliefMode
from cardforge.domain.relief import Relief
from cardforge.domain.material import DEFAULT_MATERIALS


def _make_card(features_front=None, features_back=None):
    front = Face(id="front", width=85, height=54)
    back = Face(id="back", width=85, height=54)
    if features_front:
        front.layers = [Layer(id="content", features=features_front)]
    if features_back:
        back.layers = [Layer(id="content", features=features_back)]
    return Card(
        id="test", name="Test", width=85, height=54, thickness=1.8,
        corner_radius=4, materials=DEFAULT_MATERIALS,
        faces={"front": front, "back": back},
    )


class TestGeometryBuilder:
    def test_build_returns_document(self):
        card = _make_card()
        builder = GeometryBuilder()
        doc = builder.build(card)
        assert isinstance(doc, DocumentNode)
        assert doc.name == "Test"

    def test_document_has_union_root(self):
        card = _make_card()
        builder = GeometryBuilder()
        doc = builder.build(card)
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], UnionNode)

    def test_card_base_is_extruded_rounded_rect(self):
        card = _make_card()
        builder = GeometryBuilder()
        doc = builder.build(card)
        union = doc.children[0]
        base_extrude = union.children[0]
        assert isinstance(base_extrude, ExtrudeNode)
        assert base_extrude.height == 1.8

    def test_text_feature_becomes_text_node(self):
        text = TextBlockFeature(
            id="hello", lines=["Hello"],
            position=Position(10, 20), size=Size(40, 10),
            relief=Relief.emboss(0.4),
        )
        card = _make_card(features_front=[text])
        builder = GeometryBuilder()
        doc = builder.build(card)
        text_nodes = _find_nodes_of_type(doc, TextNode)
        assert len(text_nodes) >= 1

    def test_qr_feature_becomes_svg_node(self, tmp_path):
        qr = QRCodeFeature(
            id="qr1", position=Position(56, 15), size=Size(24, 24),
        )
        card = _make_card(features_back=[qr])

        # Create fake QR asset
        assets = GeneratedAssets()
        qr_path = tmp_path / "qr_qr1.svg"
        qr_path.write_text("<svg></svg>")
        assets.qr_paths.append(qr_path)

        builder = GeometryBuilder()
        doc = builder.build(card, assets)
        svg_nodes = _find_nodes_of_type(doc, SVGNode)
        assert len(svg_nodes) == 1

    def test_back_face_has_mirror(self):
        text = TextBlockFeature(
            id="back_text", lines=["Back"],
            position=Position(10, 10), size=Size(20, 10),
        )
        card = _make_card(features_back=[text])
        builder = GeometryBuilder()
        doc = builder.build(card)
        mirror_nodes = _find_nodes_of_type(doc, MirrorNode)
        assert len(mirror_nodes) >= 1

    def test_invisible_features_excluded(self):
        hidden = TextBlockFeature(
            id="hidden", lines=["X"], visible=False,
            position=Position(0, 0), size=Size(10, 10),
        )
        card = _make_card(features_front=[hidden])
        builder = GeometryBuilder()
        doc = builder.build(card)
        text_nodes = _find_nodes_of_type(doc, TextNode)
        assert len(text_nodes) == 0

    def test_metadata_on_nodes(self):
        text = TextBlockFeature(
            id="meta_test", lines=["M"], material=DEFAULT_MATERIALS["accent"],
            position=Position(10, 10), size=Size(20, 10),
        )
        card = _make_card(features_front=[text])
        builder = GeometryBuilder()
        doc = builder.build(card)
        text_nodes = _find_nodes_of_type(doc, TextNode)
        assert len(text_nodes) == 1
        assert text_nodes[0].metadata.get("source_feature") == "meta_test"
        assert text_nodes[0].metadata.get("material") == "accent"


def _find_nodes_of_type(root, node_type):
    """Find all nodes of a given type in the tree."""
    result = []
    if isinstance(root, node_type):
        result.append(root)
    if hasattr(root, 'children'):
        for child in root.children:
            result.extend(_find_nodes_of_type(child, node_type))
    return result
