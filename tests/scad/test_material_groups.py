"""Tests for material grouping — group features by material for multi-color STL."""

from cardforge.scad.material_groups import group_features_by_material
from cardforge.domain.card import Card
from cardforge.domain.face import Face
from cardforge.domain.layer import Layer
from cardforge.domain.feature import TextBlockFeature, QRCodeFeature, PatternFeature, LogoFeature
from cardforge.domain.geometry import Position, Size
from cardforge.domain.material import Material, DEFAULT_MATERIALS


def _make_card(features_front=None, features_back=None):
    """Create a test card with given features."""
    front = Face(id="front", width=85, height=54)
    back = Face(id="back", width=85, height=54)
    if features_front:
        front.layers = [Layer(id="content", features=features_front)]
    if features_back:
        back.layers = [Layer(id="content", features=features_back)]
    return Card(
        id="test", name="Test", width=85, height=54, thickness=1.8,
        materials=DEFAULT_MATERIALS,
        faces={"front": front, "back": back},
    )


class TestMaterialGroups:
    def test_base_always_present(self):
        """Base material group should always exist even with no features."""
        card = _make_card()
        groups = group_features_by_material(card)
        assert "base" in groups

    def test_groups_features_by_material(self):
        """Features with different materials go to different groups."""
        text = TextBlockFeature(
            id="t1", lines=["Hello"], material=DEFAULT_MATERIALS["text"],
            position=Position(10, 10), size=Size(20, 10),
        )
        accent = LogoFeature(
            id="logo1", svg_file="logo.svg", material=DEFAULT_MATERIALS["accent"],
            position=Position(30, 10), size=Size(20, 20),
        )
        card = _make_card(features_front=[text, accent])
        groups = group_features_by_material(card)
        assert "text" in groups
        assert "accent" in groups
        assert len(groups["text"]) == 1
        assert len(groups["accent"]) == 1

    def test_ignores_invisible_features(self):
        """Invisible features should be excluded from groups."""
        hidden = TextBlockFeature(
            id="hidden", lines=["X"], visible=False,
            material=DEFAULT_MATERIALS["text"],
            position=Position(0, 0), size=Size(10, 10),
        )
        card = _make_card(features_front=[hidden])
        groups = group_features_by_material(card)
        assert len(groups.get("text", [])) == 0

    def test_includes_both_faces(self):
        """Features from front and back should be in the same material group."""
        front_text = TextBlockFeature(
            id="front", lines=["F"], material=DEFAULT_MATERIALS["text"],
            position=Position(10, 10), size=Size(10, 10),
        )
        back_text = TextBlockFeature(
            id="back", lines=["B"], material=DEFAULT_MATERIALS["text"],
            position=Position(10, 10), size=Size(10, 10),
        )
        card = _make_card(features_front=[front_text], features_back=[back_text])
        groups = group_features_by_material(card)
        assert len(groups["text"]) == 2

    def test_preserves_z_index_order(self):
        """Features should be sorted by z_index within each group."""
        top = TextBlockFeature(
            id="top", lines=["Top"], z_index=10,
            material=DEFAULT_MATERIALS["text"],
            position=Position(0, 0), size=Size(10, 10),
        )
        bottom = TextBlockFeature(
            id="bottom", lines=["Bottom"], z_index=1,
            material=DEFAULT_MATERIALS["text"],
            position=Position(0, 0), size=Size(10, 10),
        )
        card = _make_card(features_front=[top, bottom])
        groups = group_features_by_material(card)
        text_features = groups["text"]
        assert text_features[0].id == "bottom"
        assert text_features[1].id == "top"

    def test_multiple_feature_types_same_material(self):
        """QR and text can share the same material group."""
        text = TextBlockFeature(
            id="t1", lines=["Hello"],
            material=DEFAULT_MATERIALS["text"],
            position=Position(10, 10), size=Size(20, 10),
        )
        qr = QRCodeFeature(
            id="qr1", material=DEFAULT_MATERIALS["text"],
            position=Position(50, 10), size=Size(24, 24),
        )
        card = _make_card(features_back=[text, qr])
        groups = group_features_by_material(card)
        assert len(groups["text"]) == 2

    def test_pattern_features_grouped(self):
        """Pattern features should be grouped by their material."""
        pat = PatternFeature(
            id="bg", pattern_type="text-repeat", text="JR",
            material=DEFAULT_MATERIALS["base"], face="front",
        )
        card = _make_card(features_front=[pat])
        groups = group_features_by_material(card)
        assert len(groups["base"]) == 1

    def test_qr_features_grouped(self):
        """QR features group correctly."""
        qr = QRCodeFeature(
            id="vcard_qr", material=DEFAULT_MATERIALS["text"],
            position=Position(50, 15), size=Size(24, 24),
        )
        card = _make_card(features_back=[qr])
        groups = group_features_by_material(card)
        assert len(groups["text"]) == 1

    def test_custom_material(self):
        """Custom materials should create their own group."""
        custom_mat = Material(id="neon", name="Neon", color="#ff00ff")
        feat = TextBlockFeature(
            id="neon_text", lines=["Glow"], material=custom_mat,
            position=Position(0, 0), size=Size(10, 10),
        )
        card = _make_card(features_front=[feat])
        groups = group_features_by_material(card)
        assert "neon" in groups
        assert len(groups["neon"]) == 1

    def test_returns_dict_of_lists(self):
        """Result should be a dict mapping material_id -> list of features."""
        card = _make_card()
        groups = group_features_by_material(card)
        assert isinstance(groups, dict)
        for key, value in groups.items():
            assert isinstance(key, str)
            assert isinstance(value, list)
