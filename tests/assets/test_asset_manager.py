"""Tests for asset manager."""

from cardforge.assets.asset_manager import generate_assets, GeneratedAssets
from cardforge.domain.card import Card
from cardforge.domain.face import Face
from cardforge.domain.layer import Layer
from cardforge.domain.feature import QRCodeFeature, PatternFeature, TextBlockFeature
from cardforge.domain.material import DEFAULT_MATERIALS
from cardforge.export.paths import prepare_export_paths


def _make_card_with_features(features_front=None, features_back=None):
    front = Face(id="front", width=85, height=54)
    back = Face(id="back", width=85, height=54)
    if features_front:
        front.layers = [Layer(id="content", features=features_front)]
    if features_back:
        back.layers = [Layer(id="content", features=features_back)]
    return Card(
        id="test", name="Test", width=85, height=54, thickness=1.8,
        materials=DEFAULT_MATERIALS, faces={"front": front, "back": back},
    )


class TestAssetManager:
    def test_generates_qr_svg(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        qr = QRCodeFeature(id="qr1", qr_type="text", target="owner")
        card = _make_card_with_features(features_back=[qr])
        config = {"owner": {"name": "Javier"}}
        assets = generate_assets(card, config, export)
        assert len(assets.qr_paths) == 1
        assert assets.qr_paths[0].exists()
        content = assets.qr_paths[0].read_text()
        assert "<svg" in content

    def test_generates_vcard_qr(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        qr = QRCodeFeature(id="qr1", qr_type="vcard", target="owner")
        card = _make_card_with_features(features_back=[qr])
        config = {"owner": {"name": "Javier", "email": "j@test.com"}}
        assets = generate_assets(card, config, export)
        assert len(assets.qr_paths) == 1
        assert assets.qr_paths[0].exists()

    def test_generates_pattern_svg(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        pat = PatternFeature(id="bg", text="JR", spacing=10, pattern_type="text-repeat",
                             face="front", rotation_degrees=-25)
        card = _make_card_with_features(features_front=[pat])
        config = {}
        assets = generate_assets(card, config, export)
        assert len(assets.pattern_paths) == 1
        assert assets.pattern_paths[0].exists()
        content = assets.pattern_paths[0].read_text()
        assert "<svg" in content

    def test_all_paths(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        qr = QRCodeFeature(id="qr1", qr_type="text", target="owner")
        pat = PatternFeature(id="bg", text="X", spacing=10, pattern_type="text-repeat", face="front")
        card = _make_card_with_features(features_front=[pat], features_back=[qr])
        config = {"owner": {"name": "Test"}}
        assets = generate_assets(card, config, export)
        assert len(assets.all_paths) == 2
