"""Tests for domain factory — config → Card conversion."""

import pytest
from cardforge.domain.factory import create_card_from_config, FactoryError
from cardforge.domain.build_context import BuildContext


class TestFactory:
    """Test creating Card objects from resolved config dicts."""

    def _minimal_config(self):
        return {
            "project": {"name": "Test Card", "type": "business-card", "version": "0.1.0"},
            "manufacturing": {"process": "fdm", "nozzle": 0.4, "layerHeight": 0.2, "units": "mm"},
            "object": {"width": 85, "height": 54, "thickness": 1.8, "cornerRadius": 4},
            "faces": {
                "front": {"features": []},
                "back": {"features": []},
            },
        }

    def test_creates_card_from_minimal_config(self):
        card = create_card_from_config(self._minimal_config())
        assert card.name == "Test Card"
        assert card.width == 85
        assert card.height == 54
        assert card.thickness == 1.8
        assert card.corner_radius == 4.0
        assert card.object_type == "business-card"

    def test_creates_front_and_back_faces(self):
        card = create_card_from_config(self._minimal_config())
        assert card.get_face("front") is not None
        assert card.get_face("back") is not None
        assert card.front.width == 85
        assert card.back.height == 54

    def test_creates_text_block_feature(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "greeting",
                "type": "text-block",
                "lines": ["Hello World"],
                "font": "Montserrat",
                "fontSize": 3.2,
                "fontStyle": "bold",
                "position": {"x": 10, "y": 20},
                "size": {"width": 40, "height": 15},
                "zIndex": 1,
            }
        ]
        card = create_card_from_config(config)
        features = card.front.all_features()
        assert len(features) == 1
        f = features[0]
        assert f.id == "greeting"
        assert f.type == "text-block"
        assert f.lines == ["Hello World"]
        assert f.font_size == 3.2
        assert f.z_index == 1

    def test_creates_qr_code_feature_from_inline(self):
        config = self._minimal_config()
        config["qr"] = {
            "enabled": True,
            "type": "vcard",
            "target": "owner",
            "size": 24,
            "errorCorrection": "M",
            "quietZone": 2,
        }
        config["faces"]["back"]["features"] = [
            {
                "id": "vcard_qr",
                "type": "qr",
                "source": "qr",
                "position": {"x": 56, "y": 15},
                "size": {"width": 24, "height": 24},
                "zIndex": 2,
            }
        ]
        card = create_card_from_config(config)
        features = card.back.all_features()
        assert len(features) == 1
        f = features[0]
        assert f.id == "vcard_qr"
        assert f.type == "qr"
        assert f.qr_type == "vcard"

    def test_creates_pattern_feature(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "bg_monogram",
                "type": "pattern",
                "patternType": "text-repeat",
                "text": "JR",
                "spacing": 7,
                "rotation": -25,
                "zIndex": 0,
            }
        ]
        card = create_card_from_config(config)
        f = card.front.all_features()[0]
        assert f.type == "pattern"
        assert f.pattern_type == "text-repeat"
        assert f.text == "JR"

    def test_creates_logo_feature(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "company_logo",
                "type": "logo",
                "file": "assets/logos/logo.svg",
                "position": {"x": 42.5, "y": 27},
                "size": {"width": 24},
            }
        ]
        card = create_card_from_config(config)
        f = card.front.all_features()[0]
        assert f.type == "logo"
        assert f.svg_file == "assets/logos/logo.svg"

    def test_unknown_feature_type_raises(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {"id": "weird", "type": "flux-capacitor"}
        ]
        with pytest.raises(FactoryError, match="Unknown feature type"):
            create_card_from_config(config)

    def test_features_have_material(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "accent_text",
                "type": "text-block",
                "lines": ["Gold text"],
                "material": "accent",
                "fontSize": 3.0,
            }
        ]
        card = create_card_from_config(config)
        f = card.front.all_features()[0]
        assert f.material is not None
        assert f.material.id == "accent"

    def test_multiple_features_on_different_faces(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {"id": "f_logo", "type": "logo", "file": "logo.svg", "zIndex": 1}
        ]
        config["faces"]["back"]["features"] = [
            {"id": "b_text", "type": "text-block", "lines": ["Contact"], "fontSize": 3.0, "zIndex": 1},
            {"id": "b_qr", "type": "qr", "source": "qr", "zIndex": 2},
        ]
        card = create_card_from_config(config)
        assert len(card.front.all_features()) == 1
        assert len(card.back.all_features()) == 2

    def test_all_features_query(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {"id": "f1", "type": "text-block", "lines": ["A"], "fontSize": 3.0}
        ]
        config["faces"]["back"]["features"] = [
            {"id": "b1", "type": "text-block", "lines": ["B"], "fontSize": 3.0}
        ]
        card = create_card_from_config(config)
        all_f = card.all_features()
        assert len(all_f) == 2

    def test_context_collects_warnings_for_unknown_material(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "f1",
                "type": "text-block",
                "lines": ["Test"],
                "material": "neon_pink",
                "fontSize": 3.0,
            }
        ]
        ctx = BuildContext()
        card = create_card_from_config(config, context=ctx)
        assert len(ctx.warnings) >= 1
        # Should have fallen back to base material
        f = card.front.all_features()[0]
        assert f.material.id == "base"

    def test_features_by_material_query(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "f1",
                "type": "text-block",
                "lines": ["A"],
                "material": "accent",
                "fontSize": 3.0,
            },
            {
                "id": "f2",
                "type": "text-block",
                "lines": ["B"],
                "material": "base",
                "fontSize": 3.0,
            },
        ]
        card = create_card_from_config(config)
        accent_feats = card.features_by_material("accent")
        assert len(accent_feats) == 1
        assert accent_feats[0].id == "f1"

        base_feats = card.features_by_material("base")
        assert len(base_feats) == 1
        assert base_feats[0].id == "f2"

    def test_features_with_relief(self):
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "embossed_text",
                "type": "text-block",
                "lines": ["Raised"],
                "fontSize": 3.0,
                "relief": {"mode": "emboss", "height": 0.4},
            }
        ]
        card = create_card_from_config(config)
        f = card.front.all_features()[0]
        assert f.relief.mode.value == "emboss"
        assert f.relief.height == 0.4
