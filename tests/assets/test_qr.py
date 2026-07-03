"""Tests for QR matrix generation and vCard building."""

import pytest

from cardforge.assets.qr import generate_qr_matrix
from cardforge.assets.vcard import build_vcard


class TestVCard:
    def test_builds_basic_vcard(self):
        vcard = build_vcard({
            "name": "Javier Rodriguez",
            "title": "Frontend Developer",
            "email": "javier@example.com",
        })
        assert "BEGIN:VCARD" in vcard
        assert "VERSION:3.0" in vcard
        assert "FN:Javier Rodriguez" in vcard
        assert "TITLE:Frontend Developer" in vcard
        assert "EMAIL:javier@example.com" in vcard
        assert "END:VCARD" in vcard

    def test_includes_optional_fields(self):
        vcard = build_vcard({
            "name": "X",
            "website": "https://example.com",
            "github": "xgh",
            "linkedin": "xin",
        })
        assert "URL:https://example.com" in vcard
        assert "NOTE:GitHub:" in vcard
        assert "NOTE:LinkedIn:" in vcard

    def test_minimal_owner(self):
        vcard = build_vcard({"name": "Min"})
        assert "FN:Min" in vcard


class TestQRMatrix:
    def test_generates_square_matrix(self):
        m = generate_qr_matrix("https://example.com")
        assert len(m) >= 21  # version 1 is 21×21
        assert all(len(row) == len(m) for row in m)
        assert all(isinstance(cell, bool) for row in m for cell in row)

    def test_finder_pattern_corner_dark(self):
        m = generate_qr_matrix("test")
        assert m[0][0] is True
        assert m[0][6] is True
        assert m[6][0] is True

    def test_longer_payload_bigger_matrix(self):
        small = generate_qr_matrix("x")
        big = generate_qr_matrix("https://example.com/" + "a" * 120)
        assert len(big) > len(small)

    def test_higher_ec_not_smaller(self):
        low = generate_qr_matrix("https://example.com/page", "L")
        high = generate_qr_matrix("https://example.com/page", "H")
        assert len(high) >= len(low)

    def test_empty_value_raises(self):
        with pytest.raises(ValueError):
            generate_qr_matrix("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            generate_qr_matrix("   ")

    def test_invalid_error_correction_raises(self):
        with pytest.raises(ValueError):
            generate_qr_matrix("x", "Z")
