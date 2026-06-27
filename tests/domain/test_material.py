"""Tests for Material and Relief domain models."""

import pytest
from cardforge.domain.material import Material, DEFAULT_MATERIALS
from cardforge.domain.relief import Relief
from cardforge.domain.geometry import ReliefMode


class TestMaterial:
    def test_create_valid_material(self):
        m = Material(id="gold", name="Gold PLA", color="#ffd700", role="accent")
        assert m.id == "gold"
        assert m.name == "Gold PLA"
        assert m.color == "#ffd700"
        assert m.role == "accent"

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Material(id="", name="Test", color="#000")

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Material(id="test", name="", color="#000")

    def test_invalid_color_raises(self):
        with pytest.raises(ValueError, match="hex"):
            Material(id="test", name="Test", color="red")

    def test_equality_by_id(self):
        a = Material(id="gold", name="Gold", color="#ffd700")
        b = Material(id="gold", name="Different Name", color="#000000")
        assert a == b

    def test_hash_by_id(self):
        a = Material(id="gold", name="Gold", color="#ffd700")
        b = Material(id="gold", name="Other", color="#000")
        assert hash(a) == hash(b)

    def test_to_dict(self):
        m = Material(id="base", name="Black PLA", color="#1a1a1a", role="base")
        d = m.to_dict()
        assert d == {"id": "base", "name": "Black PLA", "color": "#1a1a1a", "role": "base"}

    def test_default_materials_exist(self):
        assert "base" in DEFAULT_MATERIALS
        assert "text" in DEFAULT_MATERIALS
        assert "accent" in DEFAULT_MATERIALS
        assert DEFAULT_MATERIALS["base"].role == "base"
        assert DEFAULT_MATERIALS["text"].role == "text"


class TestRelief:
    def test_default_is_flush(self):
        r = Relief()
        assert r.mode == ReliefMode.FLUSH
        assert r.height is None
        assert r.depth is None

    def test_emboss_valid(self):
        r = Relief(mode=ReliefMode.EMBOSS, height=0.4)
        assert r.mode == ReliefMode.EMBOSS
        assert r.height == 0.4

    def test_emboss_missing_height_raises(self):
        with pytest.raises(ValueError, match="height"):
            Relief(mode=ReliefMode.EMBOSS)

    def test_emboss_zero_height_raises(self):
        with pytest.raises(ValueError, match="> 0"):
            Relief(mode=ReliefMode.EMBOSS, height=0)

    def test_emboss_negative_height_raises(self):
        with pytest.raises(ValueError, match="> 0"):
            Relief(mode=ReliefMode.EMBOSS, height=-0.1)

    def test_emboss_with_depth_raises(self):
        with pytest.raises(ValueError, match="depth"):
            Relief(mode=ReliefMode.EMBOSS, height=0.4, depth=0.2)

    def test_deboss_valid(self):
        r = Relief(mode=ReliefMode.DEBOSS, depth=0.2)
        assert r.mode == ReliefMode.DEBOSS
        assert r.depth == 0.2

    def test_deboss_missing_depth_raises(self):
        with pytest.raises(ValueError, match="depth"):
            Relief(mode=ReliefMode.DEBOSS)

    def test_deboss_with_height_raises(self):
        with pytest.raises(ValueError, match="height"):
            Relief(mode=ReliefMode.DEBOSS, depth=0.2, height=0.4)

    def test_cut_valid(self):
        r = Relief(mode=ReliefMode.CUT, depth=1.8)
        assert r.mode == ReliefMode.CUT
        assert r.depth == 1.8

    def test_cut_missing_depth_raises(self):
        with pytest.raises(ValueError, match="depth"):
            Relief(mode=ReliefMode.CUT)

    def test_flush_valid_no_params(self):
        r = Relief(mode=ReliefMode.FLUSH)
        assert r.mode == ReliefMode.FLUSH

    def test_to_dict_emboss(self):
        r = Relief.emboss(0.5)
        d = r.to_dict()
        assert d == {"mode": "emboss", "height": 0.5}

    def test_to_dict_deboss(self):
        r = Relief.deboss(0.2)
        d = r.to_dict()
        assert d == {"mode": "deboss", "depth": 0.2}

    def test_to_dict_flush(self):
        r = Relief.flush()
        d = r.to_dict()
        assert d == {"mode": "flush"}

    def test_factory_emboss(self):
        r = Relief.emboss(0.4)
        assert r.mode == ReliefMode.EMBOSS
        assert r.height == 0.4

    def test_factory_deboss(self):
        r = Relief.deboss(0.2)
        assert r.mode == ReliefMode.DEBOSS
        assert r.depth == 0.2

    def test_factory_flush(self):
        r = Relief.flush()
        assert r.mode == ReliefMode.FLUSH

    def test_factory_cut(self):
        r = Relief.cut(1.0)
        assert r.mode == ReliefMode.CUT
        assert r.depth == 1.0
