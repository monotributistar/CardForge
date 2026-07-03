"""QR manufacturing validations — size, contrast, quiet zone, opacity."""

import pytest

from cardforge.document.schema_v2 import DocumentV2
from cardforge.kernel.compile import compile_document
from cardforge.manufacturing.analyzer import ManufacturingAnalyzer, resolve_profile
from cardforge.manufacturing.color import contrast_ratio
from cardforge.manufacturing.issues import IssueCode, Severity


def doc(qr, base_color="#1a1a1a", extra=(), materials=None):
    mats = materials or [
        {"id": "base", "name": "B", "color": base_color, "role": "base"},
        {"id": "text", "name": "W", "color": "#ffffff", "role": "text"}]
    return DocumentV2.from_dict({
        "cardforge": "2.0", "meta": {"id": "t", "name": "T"},
        "object": {"outline": {"type": "rect", "width": 60, "height": 50}, "thickness": 2.0},
        "manufacturing": {"nozzle": 0.4, "layerHeight": 0.2},
        "materials": mats,
        "faces": {"back": {"features": [qr, *extra]}},
    })


def qr(material="text", relief=None, size=24, quiet=2.0):
    return {"id": "qr", "type": "qr", "transform": {"x": 5, "y": 5},
            "material": material, "relief": relief or {"mode": "flush", "depth": 0.4},
            "qrType": "url", "fields": {"url": "https://example.com"},
            "size": size, "quietZone": quiet}


def issues(d):
    scene, trace = compile_document(d)
    return ManufacturingAnalyzer(resolve_profile(d)).analyze(d, scene, trace).issues


def codes(d):
    return [(i.severity, i.code) for i in issues(d)]


class TestContrastMetric:
    def test_black_white_high(self):
        assert contrast_ratio("#000000", "#ffffff") > 15

    def test_identical_is_one(self):
        assert contrast_ratio("#1a1a1a", "#1a1a1a") == pytest.approx(1.0)

    def test_gold_on_black_ok(self):
        assert contrast_ratio("#d4af37", "#1a1a1a") > 4


class TestQRContrast:
    def test_ideal_flush_contrasting_is_clean(self):
        # the recommended bed-face coloured QR: white flush on black
        assert (Severity.ERROR, IssueCode.QR_CONTRAST) not in codes(doc(qr()))
        assert (Severity.WARNING, IssueCode.QR_CONTRAST) not in codes(doc(qr()))

    def test_flush_same_as_base_is_error(self):
        c = codes(doc(qr(material="base", relief={"mode": "flush", "depth": 0.4})))
        assert (Severity.ERROR, IssueCode.QR_CONTRAST) in c

    def test_relief_same_colour_is_warning(self):
        c = codes(doc(qr(material="base", relief={"mode": "deboss", "depth": 0.3})))
        assert (Severity.WARNING, IssueCode.QR_CONTRAST) in c
        assert (Severity.ERROR, IssueCode.QR_CONTRAST) not in c


class TestQROpacity:
    def test_shallow_coloured_inlay_warns(self):
        c = codes(doc(qr(relief={"mode": "flush", "depth": 0.2})))
        assert (Severity.WARNING, IssueCode.QR_OPACITY) in c

    def test_two_layer_inlay_ok(self):
        c = codes(doc(qr(relief={"mode": "flush", "depth": 0.4})))
        assert (Severity.WARNING, IssueCode.QR_OPACITY) not in c


class TestQRQuietZone:
    def test_small_quiet_zone_warns(self):
        c = codes(doc(qr(quiet=1.0)))
        assert (Severity.WARNING, IssueCode.QR_QUIET_ZONE) in c

    def test_feature_in_quiet_zone_warns(self):
        blob = {"id": "blob", "type": "shape", "shapeType": "rect",
                "width": 6, "height": 6, "transform": {"x": 31, "y": 6},
                "material": "text", "relief": {"mode": "flush", "depth": 0.3}}
        c = codes(doc(qr(quiet=2.0), extra=[blob]))
        assert (Severity.WARNING, IssueCode.QR_QUIET_ZONE) in c

    def test_clean_qr_no_quiet_warning(self):
        c = codes(doc(qr(quiet=2.0)))
        assert (Severity.WARNING, IssueCode.QR_QUIET_ZONE) not in c


class TestQRSize:
    def test_small_qr_size_error(self):
        c = codes(doc(qr(size=15)))
        assert (Severity.ERROR, IssueCode.QR_TOO_SMALL) in c
