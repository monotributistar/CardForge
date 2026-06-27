"""Tests for Layer, Face, and Card domain models."""

import pytest
from cardforge.domain.layer import Layer
from cardforge.domain.face import Face
from cardforge.domain.card import Card
from cardforge.domain.feature import TextBlockFeature, QRCodeFeature, FrameFeature
from cardforge.domain.geometry import Position, Size
from cardforge.domain.material import Material, DEFAULT_MATERIALS
from cardforge.domain.relief import Relief


class TestLayer:
    def test_empty_layer(self):
        layer = Layer(id="content")
        assert layer.all_features() == []
        assert layer.sorted_features() == []
        assert layer.bounds() == layer.bounds()  # empty bounds

    def test_layer_with_features(self):
        f1 = TextBlockFeature(id="f1", z_index=2, lines=["A"])
        f2 = TextBlockFeature(id="f2", z_index=1, lines=["B"])
        layer = Layer(id="content", features=[f1, f2])
        assert len(layer.all_features()) == 2

    def test_sorted_features_by_z_index(self):
        f1 = TextBlockFeature(id="f1", z_index=3, lines=["Top"])
        f2 = TextBlockFeature(id="f2", z_index=1, lines=["Bottom"])
        f3 = TextBlockFeature(id="f3", z_index=2, lines=["Mid"])
        layer = Layer(id="content", features=[f1, f2, f3])
        sorted_feats = layer.sorted_features()
        assert sorted_feats[0].id == "f2"  # z=1
        assert sorted_feats[1].id == "f3"  # z=2
        assert sorted_feats[2].id == "f1"  # z=3

    def test_features_by_material(self):
        gold = Material(id="gold", name="Gold", color="#ffd700")
        black = Material(id="base", name="Black", color="#000")
        f1 = TextBlockFeature(id="f1", lines=["A"], material=gold)
        f2 = TextBlockFeature(id="f2", lines=["B"], material=black)
        layer = Layer(id="content", features=[f1, f2])
        gold_feats = layer.features_by_material(gold)
        assert len(gold_feats) == 1
        assert gold_feats[0].id == "f1"

    def test_invisible_features_not_in_bounds(self):
        f1 = TextBlockFeature(
            id="f1", lines=["A"],
            position=Position(10, 10), size=Size(50, 30), visible=False,
        )
        layer = Layer(id="content", features=[f1])
        b = layer.bounds()
        # No visible features → empty bounds
        assert b.width == 0

    def test_layer_to_dict(self):
        f1 = TextBlockFeature(
            id="hello", lines=["Hi"],
            position=Position(10, 10), size=Size(40, 10),
        )
        layer = Layer(id="content", name="Content", role="content", features=[f1])
        d = layer.to_dict()
        assert d["id"] == "content"
        assert len(d["features"]) == 1


class TestFace:
    def test_empty_face(self):
        face = Face(id="front")
        assert face.all_features() == []
        assert face.sorted_features() == []

    def test_face_with_layer(self):
        f1 = TextBlockFeature(id="f1", lines=["A"])
        layer = Layer(id="content", features=[f1])
        face = Face(id="front", layers=[layer])
        assert len(face.all_features()) == 1

    def test_face_bounds(self):
        face = Face(id="front", width=85, height=54)
        b = face.bounds()
        assert b.width == 85
        assert b.height == 54
        assert b.x == 0
        assert b.y == 0

    def test_sorted_features_across_layers(self):
        f1 = TextBlockFeature(id="base", z_index=0, lines=["Base"])
        f2 = TextBlockFeature(id="top", z_index=10, lines=["Top"])
        layer1 = Layer(id="bg", z_index=0, features=[f1])
        layer2 = Layer(id="fg", z_index=1, features=[f2])
        face = Face(id="front", layers=[layer2, layer1])  # out of order
        sorted_feats = face.sorted_features()
        assert sorted_feats[0].id == "base"
        assert sorted_feats[1].id == "top"

    def test_features_by_material(self):
        gold = Material(id="gold", name="Gold", color="#ffd700")
        f1 = TextBlockFeature(id="f1", lines=["A"], material=gold)
        layer = Layer(id="content", features=[f1])
        face = Face(id="front", layers=[layer])
        gold_feats = face.features_by_material(gold)
        assert len(gold_feats) == 1

    def test_get_layer(self):
        layer = Layer(id="content")
        face = Face(id="front", layers=[layer])
        assert face.get_layer("content") is layer
        assert face.get_layer("nonexistent") is None


class TestCard:
    def _make_card(self):
        f1 = TextBlockFeature(id="hello", lines=["Hello"], z_index=1)
        f2 = QRCodeFeature(id="qr1", z_index=2)
        layer = Layer(id="content", features=[f1, f2])
        front = Face(id="front", width=85, height=54, layers=[layer])
        back = Face(id="back", width=85, height=54, layers=[Layer(id="content")])
        return Card(
            id="test_card",
            name="Test Card",
            width=85,
            height=54,
            thickness=1.8,
            materials=DEFAULT_MATERIALS,
            faces={"front": front, "back": back},
        )

    def test_get_face(self):
        card = self._make_card()
        assert card.get_face("front") is not None
        assert card.get_face("back") is not None
        assert card.get_face("nonexistent") is None

    def test_front_back_properties(self):
        card = self._make_card()
        assert card.front is not None
        assert card.back is not None

    def test_all_features(self):
        card = self._make_card()
        all_f = card.all_features()
        assert len(all_f) == 2  # 2 on front, 0 on back

    def test_features_by_material(self):
        card = self._make_card()
        feats = card.features_by_material("base")
        # All features default to None material → won't match
        assert len(feats) == 0

    def test_sorted_features(self):
        card = self._make_card()
        sorted_f = card.sorted_features()
        assert sorted_f[0].id == "hello"
        assert sorted_f[1].id == "qr1"

    def test_card_bounds(self):
        card = self._make_card()
        b = card.bounds()
        assert b.width == 85
        assert b.height == 54

    def test_card_size(self):
        card = self._make_card()
        s = card.size()
        assert s.width == 85
        assert s.height == 54

    def test_card_to_dict(self):
        card = self._make_card()
        d = card.to_dict()
        assert d["id"] == "test_card"
        assert "materials" in d
        assert "faces" in d
