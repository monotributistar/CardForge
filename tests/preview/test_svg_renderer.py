"""Tests for SVG preview renderer."""

import pytest
from pathlib import Path
from cardforge.preview.svg_renderer import render_face_preview_svg
from cardforge.preview.theme import Theme
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.domain.card import Card
from cardforge.domain.face import Face
from cardforge.domain.layer import Layer
from cardforge.domain.feature import (
    TextBlockFeature, QRCodeFeature, PatternFeature, FrameFeature, LogoFeature,
)
from cardforge.domain.geometry import Position, Size
from cardforge.domain.material import DEFAULT_MATERIALS, Material


def _make_card(features_front=None, features_back=None):
    front = Face(id="front", width=85, height=54)
    back = Face(id="back", width=85, height=54)
    if features_front:
        front.layers = [Layer(id="content", features=features_front)]
    if features_back:
        back.layers = [Layer(id="content", features=features_back)]
    return Card(
        id="test", name="Test Card", width=85, height=54, thickness=1.8,
        corner_radius=4, materials=DEFAULT_MATERIALS,
        faces={"front": front, "back": back},
    )


class TestSvgPreviewRenderer:
    def test_renders_front_face(self, tmp_path):
        card = _make_card()
        out = tmp_path / "front.svg"
        result = render_face_preview_svg(card, "front", GeneratedAssets(), out)
        assert result == out
        assert out.exists()
        content = out.read_text()
        assert "<svg" in content
        assert "</svg>" in content

    def test_renders_back_face(self, tmp_path):
        card = _make_card()
        out = tmp_path / "back.svg"
        render_face_preview_svg(card, "back", GeneratedAssets(), out)
        assert out.exists()

    def test_includes_base_rect(self, tmp_path):
        card = _make_card()
        out = tmp_path / "front.svg"
        render_face_preview_svg(card, "front", GeneratedAssets(), out)
        content = out.read_text()
        assert "<rect" in content
        assert 'fill="' in content

    def test_includes_text_features(self, tmp_path):
        text = TextBlockFeature(
            id="hello", lines=["Hello World"],
            position=Position(10, 20), size=Size(40, 10),
            font_size=3.5, font_style="bold",
        )
        card = _make_card(features_front=[text])
        out = tmp_path / "front.svg"
        render_face_preview_svg(card, "front", GeneratedAssets(), out)
        content = out.read_text()
        assert "Hello World" in content

    def test_includes_qr_image(self, tmp_path):
        qr = QRCodeFeature(
            id="qr1", position=Position(56, 15), size=Size(24, 24),
        )
        card = _make_card(features_back=[qr])
        assets = GeneratedAssets()
        qr_path = tmp_path / "assets" / "qr_qr1.svg"
        qr_path.parent.mkdir(parents=True, exist_ok=True)
        qr_path.write_text("<svg></svg>")
        assets.qr_paths.append(qr_path)

        out = tmp_path / "back.svg"
        render_face_preview_svg(card, "back", assets, out)
        content = out.read_text()
        assert "<image" in content

    def test_respects_z_index_ordering(self, tmp_path):
        bottom = TextBlockFeature(id="bottom", lines=["Behind"], z_index=0,
                                   position=Position(5, 5), size=Size(40, 10))
        top = TextBlockFeature(id="top", lines=["Front"], z_index=10,
                                position=Position(5, 15), size=Size(40, 10))
        card = _make_card(features_front=[bottom, top])
        out = tmp_path / "front.svg"
        render_face_preview_svg(card, "front", GeneratedAssets(), out)
        content = out.read_text()
        behind_pos = content.index("Behind")
        front_pos = content.index("Front")
        assert behind_pos < front_pos

    def test_ignores_invisible_features(self, tmp_path):
        hidden = TextBlockFeature(id="hidden", lines=["Invisible"], visible=False,
                                   position=Position(5, 5), size=Size(40, 10))
        card = _make_card(features_front=[hidden])
        out = tmp_path / "front.svg"
        render_face_preview_svg(card, "front", GeneratedAssets(), out)
        content = out.read_text()
        assert "Invisible" not in content

    def test_respects_material_color(self, tmp_path):
        gold_mat = Material(id="gold", name="Gold", color="#ffd700")
        text = TextBlockFeature(id="gold_text", lines=["Gold"], material=gold_mat,
                                 position=Position(10, 10), size=Size(30, 10))
        card = _make_card(features_front=[text])
        out = tmp_path / "front.svg"
        render_face_preview_svg(card, "front", GeneratedAssets(), out)
        content = out.read_text()
        assert "#ffd700" in content

    def test_invalid_face_id_raises(self, tmp_path):
        card = _make_card()
        with pytest.raises(ValueError, match="not found"):
            render_face_preview_svg(card, "side", GeneratedAssets(), tmp_path / "side.svg")

    def test_renders_frame_feature(self, tmp_path):
        frame = FrameFeature(id="border", frame_style="border", frame_width=2)
        card = _make_card(features_front=[frame])
        out = tmp_path / "front.svg"
        render_face_preview_svg(card, "front", GeneratedAssets(), out)
        content = out.read_text()
        assert 'fill="none"' in content
        assert 'stroke=' in content

    def test_renders_logo_placeholder(self, tmp_path):
        logo = LogoFeature(id="logo1", svg_file="logo.svg",
                           position=Position(30, 15), size=Size(24, 24))
        card = _make_card(features_front=[logo])
        out = tmp_path / "front.svg"
        render_face_preview_svg(card, "front", GeneratedAssets(), out)
        content = out.read_text()
        assert "LOGO" in content

    def test_multiline_text(self, tmp_path):
        text = TextBlockFeature(
            id="contact", lines=["Line 1", "Line 2", "Line 3"],
            position=Position(8, 12), size=Size(40, 30),
            font_size=3.2, line_height=1.4,
        )
        card = _make_card(features_front=[text])
        out = tmp_path / "front.svg"
        render_face_preview_svg(card, "front", GeneratedAssets(), out)
        content = out.read_text()
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content
