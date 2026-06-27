"""Tests for core geometry types: Position, Size, Bounds."""

from cardforge.domain.geometry import Position, Size, Bounds, Anchor


class TestPosition:
    def test_default_position(self):
        p = Position()
        assert p.x == 0.0
        assert p.y == 0.0

    def test_position_creation(self):
        p = Position(10.5, 20.3)
        assert p.x == 10.5
        assert p.y == 20.3

    def test_position_add(self):
        a = Position(10, 20)
        b = Position(5, 7)
        result = a + b
        assert result.x == 15
        assert result.y == 27

    def test_position_sub(self):
        a = Position(10, 20)
        b = Position(3, 5)
        result = a - b
        assert result.x == 7
        assert result.y == 15

    def test_position_to_tuple(self):
        p = Position(3.0, 4.0)
        assert p.to_tuple() == (3.0, 4.0)


class TestSize:
    def test_default_size(self):
        s = Size()
        assert s.width == 0.0
        assert s.height == 0.0

    def test_size_area(self):
        s = Size(10, 20)
        assert s.area == 200.0

    def test_size_bool_true(self):
        assert bool(Size(10, 5))

    def test_size_bool_false_zero(self):
        assert not bool(Size(0, 5))

    def test_size_bool_false_both_zero(self):
        assert not bool(Size(0, 0))

    def test_size_to_tuple(self):
        s = Size(85, 54)
        assert s.to_tuple() == (85, 54)


class TestBounds:
    def test_default_bounds(self):
        b = Bounds()
        assert b.x == 0.0
        assert b.y == 0.0
        assert b.width == 0.0
        assert b.height == 0.0

    def test_bounds_right_and_bottom(self):
        b = Bounds(10, 20, 100, 50)
        assert b.right == 110.0
        assert b.bottom == 70.0

    def test_bounds_center(self):
        b = Bounds(0, 0, 100, 60)
        c = b.center
        assert c.x == 50.0
        assert c.y == 30.0

    def test_bounds_top_left(self):
        b = Bounds(5, 10, 80, 40)
        tl = b.top_left
        assert tl.x == 5.0
        assert tl.y == 10.0

    def test_bounds_area(self):
        b = Bounds(0, 0, 85, 54)
        assert b.area == 4590.0

    def test_contains_fully_inside(self):
        outer = Bounds(0, 0, 100, 100)
        inner = Bounds(10, 10, 50, 50)
        assert outer.contains(inner)
        assert not inner.contains(outer)

    def test_contains_partial_overlap(self):
        outer = Bounds(0, 0, 100, 100)
        partial = Bounds(80, 80, 50, 50)
        assert not outer.contains(partial)

    def test_contains_same_bounds(self):
        b = Bounds(10, 20, 30, 40)
        assert b.contains(b)

    def test_intersects_overlapping(self):
        a = Bounds(0, 0, 50, 50)
        b = Bounds(25, 25, 50, 50)
        assert a.intersects(b)
        assert b.intersects(a)

    def test_intersects_disjoint(self):
        a = Bounds(0, 0, 10, 10)
        b = Bounds(100, 100, 10, 10)
        assert not a.intersects(b)

    def test_intersects_touching_edge_not_overlap(self):
        """Touching edges (adjacent) do NOT intersect."""
        a = Bounds(0, 0, 10, 10)
        b = Bounds(10, 0, 10, 10)
        assert not a.intersects(b)

    def test_intersects_contained(self):
        outer = Bounds(0, 0, 100, 100)
        inner = Bounds(20, 20, 10, 10)
        assert outer.intersects(inner)
        assert inner.intersects(outer)

    def test_expand(self):
        b = Bounds(10, 10, 80, 40)
        e = b.expand(5)
        assert e.x == 5.0
        assert e.y == 5.0
        assert e.width == 90.0
        assert e.height == 50.0

    def test_expand_zero(self):
        b = Bounds(10, 10, 80, 40)
        e = b.expand(0)
        assert e.x == b.x
        assert e.y == b.y
        assert e.width == b.width
        assert e.height == b.height

    def test_to_dict(self):
        b = Bounds(5, 10, 100, 50)
        d = b.to_dict()
        assert d == {"x": 5, "y": 10, "width": 100, "height": 50}


class TestAnchor:
    def test_all_anchors_exist(self):
        anchors = list(Anchor)
        assert len(anchors) == 9
        assert Anchor.TOP_LEFT == "top-left"
        assert Anchor.CENTER == "center"
        assert Anchor.BOTTOM_RIGHT == "bottom-right"
