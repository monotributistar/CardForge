"""Tests for SCAD generator — domain model to OpenSCAD code."""

import pytest
from pathlib import Path
from cardforge.scad.generator import generate_scad
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.export.paths import prepare_export_paths
from cardforge.domain.card import Card
from cardforge.domain.face import Face
from cardforge.domain.layer import Layer
from cardforge.domain.feature import (
    TextBlockFeature, QRCodeFeature, PatternFeature, FrameFeature,
)
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
        id="test", name="Test Card", width=85, height=54, thickness=1.8,
        corner_radius=4, materials=DEFAULT_MATERIALS,
        faces={"front": front, "back": back},
    )


class TestScadGenerator:
    def test_generates_scad_file(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        card = _make_card()
        scad_path = generate_scad(card, GeneratedAssets(), export)
        assert scad_path.exists()
        content = scad_path.read_text()
        assert "card_base(" in content
        assert "main.scad" in content

    def test_includes_card_base_params(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        card = _make_card()
        scad_path = generate_scad(card, GeneratedAssets(), export)
        content = scad_path.read_text()
        assert "width=85" in content
        assert "height=54" in content
        assert "thickness=1.8" in content

    def test_includes_text_features(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        text = TextBlockFeature(
            id="hello", lines=["Hello World"],
            position=Position(10, 20), size=Size(40, 10),
            font_size=3.5,
            relief=Relief.emboss(0.4),
        )
        card = _make_card(features_front=[text])
        scad_path = generate_scad(card, GeneratedAssets(), export)
        content = scad_path.read_text()
        assert "text_emboss_layer(" in content
        assert "Hello World" in content

    def test_includes_qr_import(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        qr = QRCodeFeature(
            id="qr1", position=Position(56, 15), size=Size(24, 24),
        )
        card = _make_card(features_back=[qr])

        # Create fake QR asset
        qr_path = export.assets_dir / "qr_qr1.svg"
        qr_path.parent.mkdir(parents=True, exist_ok=True)
        qr_path.write_text("<svg></svg>")

        assets = GeneratedAssets(qr_paths=[qr_path])
        scad_path = generate_scad(card, assets, export)
        content = scad_path.read_text()
        assert "svg_emboss_layer(" in content
        assert "qr_qr1" in content

    def test_skips_invisible_features(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        hidden = TextBlockFeature(
            id="hidden", lines=["Invisible"], visible=False,
            position=Position(0, 0), size=Size(10, 10),
        )
        card = _make_card(features_front=[hidden])
        scad_path = generate_scad(card, GeneratedAssets(), export)
        content = scad_path.read_text()
        assert "Invisible" not in content

    def test_front_and_back_sections(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        front_text = TextBlockFeature(
            id="front_text", lines=["Front"],
            position=Position(10, 10), size=Size(20, 10),
        )
        back_text = TextBlockFeature(
            id="back_text", lines=["Back"],
            position=Position(10, 10), size=Size(20, 10),
        )
        card = _make_card(features_front=[front_text], features_back=[back_text])
        scad_path = generate_scad(card, GeneratedAssets(), export)
        content = scad_path.read_text()
        assert "Front Face" in content
        assert "Back Face" in content
        assert "mirror" in content  # back face uses mirror([0,0,1])

    def test_coordinate_conversion(self, tmp_path):
        """Python top-left coords should convert to OpenSCAD centered coords."""
        export = prepare_export_paths("Test", base_dir=tmp_path)
        # Feature at top-left (0,0) in Python should be near (-42.5, 27) in SCAD
        text = TextBlockFeature(
            id="corner", lines=["A"],
            position=Position(0, 0), size=Size(10, 10),
        )
        card = _make_card(features_front=[text])
        scad_path = generate_scad(card, GeneratedAssets(), export)
        content = scad_path.read_text()
        # x should be around -42.5 (0 - 42.5)
        assert "-42.5" in content
        # y should be around 27 (27 - 0)
        assert "27" in content

    def test_z_index_ordering(self, tmp_path):
        """Features with lower zIndex should appear earlier in the file."""
        export = prepare_export_paths("Test", base_dir=tmp_path)
        bottom = TextBlockFeature(
            id="bottom", lines=["Bottom"], z_index=0,
            position=Position(5, 5), size=Size(20, 10),
        )
        top = TextBlockFeature(
            id="top", lines=["Top"], z_index=10,
            position=Position(5, 15), size=Size(20, 10),
        )
        card = _make_card(features_front=[bottom, top])
        scad_path = generate_scad(card, GeneratedAssets(), export)
        content = scad_path.read_text()
        bottom_pos = content.index("Bottom")
        top_pos = content.index("Top")
        assert bottom_pos < top_pos

    def test_generated_file_has_header(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        card = _make_card()
        scad_path = generate_scad(card, GeneratedAssets(), export)
        content = scad_path.read_text()
        assert "CardForge" in content
        assert "Auto-generated" in content

    def test_handles_pattern_feature(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        pat = PatternFeature(
            id="bg", pattern_type="text-repeat", text="JR",
            face="front", relief=Relief.deboss(0.2),
        )
        card = _make_card(features_front=[pat])

        pat_path = export.assets_dir / "pattern_front_bg.svg"
        pat_path.parent.mkdir(parents=True, exist_ok=True)
        pat_path.write_text("<svg></svg>")

        assets = GeneratedAssets(pattern_paths=[pat_path])
        scad_path = generate_scad(card, assets, export)
        content = scad_path.read_text()
        # Should reference the pattern in some way
        assert "svg_emboss_layer" in content or "pattern" in content.lower()
