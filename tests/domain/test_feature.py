"""Tests for Feature and Primitive domain models."""

from cardforge.domain.feature import (
    Feature,
    TextBlockFeature,
    QRCodeFeature,
    PatternFeature,
    LogoFeature,
    FrameFeature,
    CornerDecorationFeature,
)
from cardforge.domain.primitive import (
    Primitive,
    RectanglePrimitive,
    TextPrimitive,
    SVGPrimitive,
    GroupPrimitive,
)
from cardforge.domain.geometry import Position, Size, Bounds
from cardforge.domain.material import Material
from cardforge.domain.relief import Relief


class TestFeature:
    def test_feature_bounds(self):
        f = Feature(
            id="test",
            type="test",
            position=Position(10, 20),
            size=Size(50, 30),
        )
        b = f.bounds()
        assert b.x == 10
        assert b.y == 20
        assert b.width == 50
        assert b.height == 30

    def test_feature_defaults(self):
        f = Feature(id="f1", type="text-block")
        assert f.visible is True
        assert f.z_index == 0
        assert f.face == "front"
        assert f.layer == "content"

    def test_text_block_feature(self):
        f = TextBlockFeature(
            id="t1",
            lines=["Hello", "World"],
            font="Montserrat",
            font_size=3.5,
            font_style="bold",
        )
        assert f.type == "text-block"
        assert f.lines == ["Hello", "World"]
        assert f.font == "Montserrat"

    def test_qr_code_feature(self):
        f = QRCodeFeature(
            id="qr1",
            qr_type="vcard",
            target="owner",
            error_correction="M",
            quiet_zone=2.0,
        )
        assert f.type == "qr"
        assert f.qr_type == "vcard"
        assert f.quiet_zone == 2.0

    def test_pattern_feature(self):
        f = PatternFeature(
            id="p1",
            pattern_type="text-repeat",
            text="JR",
            spacing=7.0,
            rotation_degrees=-25,
        )
        assert f.type == "pattern"
        assert f.text == "JR"
        assert f.spacing == 7.0

    def test_logo_feature(self):
        f = LogoFeature(id="logo1", svg_file="assets/logos/logo.svg")
        assert f.type == "logo"
        assert f.svg_file == "assets/logos/logo.svg"

    def test_frame_feature(self):
        f = FrameFeature(
            id="frame1",
            frame_style="border",
            frame_width=2.0,
        )
        assert f.type == "frame"
        assert f.frame_style == "border"

    def test_corner_feature(self):
        f = CornerDecorationFeature(
            id="corner1",
            corner_style="notch",
            radius=4.0,
        )
        assert f.type == "corner"
        assert f.corner_style == "notch"

    def test_feature_with_material(self):
        mat = Material(id="gold", name="Gold", color="#ffd700")
        f = Feature(id="f1", type="text-block", material=mat)
        assert f.material == mat
        assert f.material.id == "gold"

    def test_feature_with_relief(self):
        r = Relief.emboss(0.5)
        f = Feature(id="f1", type="text-block", relief=r)
        assert f.relief.mode.value == "emboss"
        assert f.relief.height == 0.5

    def test_feature_to_dict(self):
        f = TextBlockFeature(
            id="hello",
            name="Greeting",
            position=Position(10, 20),
            size=Size(40, 10),
            lines=["Hello"],
            z_index=2,
        )
        d = f.to_dict()
        assert d["id"] == "hello"
        assert d["type"] == "text-block"
        assert d["position"] == (10, 20)
        assert d["z_index"] == 2


class TestPrimitive:
    def test_rectangle_primitive(self):
        b = Bounds(10, 10, 80, 40)
        r = RectanglePrimitive.create("r1", b)
        assert r.id == "r1"
        assert r.type == "rectangle"
        assert r.bounds == b

    def test_text_primitive(self):
        t = TextPrimitive(
            id="t1",
            lines=["Hello"],
            font_size=3.0,
        )
        assert t.type == "text"
        assert t.lines == ["Hello"]

    def test_svg_primitive(self):
        s = SVGPrimitive(id="s1", svg_path="assets/qr/test.svg")
        assert s.type == "svg"
        assert s.svg_path == "assets/qr/test.svg"

    def test_group_primitive(self):
        r1 = RectanglePrimitive.create("r1", Bounds(0, 0, 10, 10))
        r2 = RectanglePrimitive.create("r2", Bounds(10, 10, 10, 10))
        g = GroupPrimitive(id="g1", children=[r1, r2])
        assert len(g.children) == 2
        assert g.type == "group"
