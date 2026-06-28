"""Tests for ManufacturingAnalyzer — Visitor on Geometry IR."""

import pytest
from cardforge.manufacturing.analyzer import ManufacturingAnalyzer
from cardforge.manufacturing.profiles import ManufacturingProfile
from cardforge.manufacturing.report import ManufacturingReport
from cardforge.geometry_ir.nodes import (
    DocumentNode, UnionNode, ExtrudeNode, TranslateNode,
    RoundedRectangleNode, RectangleNode, TextNode, SVGNode, GroupNode,
)


class TestManufacturingAnalyzer:
    def _profile(self):
        return ManufacturingProfile.fdm_standard()

    def test_empty_document(self):
        doc = DocumentNode(id="empty", name="Empty")
        analyzer = ManufacturingAnalyzer(self._profile())
        report = analyzer.analyze(doc)
        assert isinstance(report, ManufacturingReport)
        assert report.score == 100
        assert report.is_manufacturable

    def test_detects_text_too_small(self):
        text = TextNode(id="tiny", text="Hi", font_size=2.0)
        doc = DocumentNode(id="doc", name="Test", children=[text])
        analyzer = ManufacturingAnalyzer(self._profile())
        report = analyzer.analyze(doc)
        assert len(report.warnings) >= 1
        assert report.metrics.text_count == 1

    def test_text_ok(self):
        text = TextNode(id="ok", text="Hello", font_size=4.0)
        doc = DocumentNode(id="doc", name="Test", children=[text])
        analyzer = ManufacturingAnalyzer(self._profile())
        report = analyzer.analyze(doc)
        # 4.0mm text should pass for FDM standard
        assert len(report.issues) == 0
        assert report.metrics.smallest_text == 4.0

    def test_detects_qr_too_small(self):
        svg = SVGNode(id="qr1", file_path="qr.svg", width=15, height=15)
        doc = DocumentNode(id="doc", name="Test", children=[svg])
        analyzer = ManufacturingAnalyzer(self._profile())
        report = analyzer.analyze(doc)
        assert len(report.issues) >= 1
        assert report.metrics.svg_count == 1

    def test_qr_ok(self):
        svg = SVGNode(id="qr_code", file_path="qr.svg", width=24, height=24)
        doc = DocumentNode(id="doc", name="Test", children=[svg])
        analyzer = ManufacturingAnalyzer(self._profile())
        report = analyzer.analyze(doc)
        # 24mm QR should pass
        qr_issues = [i for i in report.issues if "QR" in i.message.upper()]
        assert len(qr_issues) == 0

    def test_emboss_too_low(self):
        p = self._profile()
        rect = RectangleNode(id="r1", width=10, height=10,
                             metadata={"relief_mode": "emboss"})
        extrude = ExtrudeNode(id="e1", height=0.15, children=[rect],
                              metadata={"relief_mode": "emboss"})
        doc = DocumentNode(id="doc", name="Test", children=[extrude])
        analyzer = ManufacturingAnalyzer(p)
        report = analyzer.analyze(doc)
        emboss_issues = [i for i in report.issues if "Emboss" in i.message]
        assert len(emboss_issues) >= 1

    def test_metrics_populated(self):
        rect = RoundedRectangleNode(id="base", width=85, height=54, radius=4)
        extrude = ExtrudeNode(id="e1", height=1.8, children=[rect],
                              metadata={"relief_mode": "emboss"})
        text = TextNode(id="t1", text="Hi", font_size=3.5)
        doc = DocumentNode(id="doc", name="Test", children=[extrude, text])
        analyzer = ManufacturingAnalyzer(self._profile())
        report = analyzer.analyze(doc)
        assert report.metrics.smallest_line > 0
        assert report.metrics.text_count >= 1
        assert report.metrics.extrude_count >= 1

    def test_score_with_multiple_issues(self):
        # Create a document with several problems
        text = TextNode(id="small_text", text="xx", font_size=2.0)
        svg = SVGNode(id="qr_code", file_path="qr.svg", width=15, height=15)
        rect = RectangleNode(id="thin", width=0.3, height=10,
                             metadata={"relief_mode": "emboss"})
        extrude = ExtrudeNode(id="e1", height=0.15, children=[rect],
                              metadata={"relief_mode": "emboss"})
        doc = DocumentNode(id="doc", name="Bad Card", children=[text, svg, extrude])
        analyzer = ManufacturingAnalyzer(self._profile())
        report = analyzer.analyze(doc)
        # Should have multiple issues
        assert len(report.issues) > 2
        assert report.score < 95

    def test_clean_document_scores_high(self):
        # A well-formed document should score high
        base = RoundedRectangleNode(id="base", width=85, height=54, radius=4)
        extrude = ExtrudeNode(id="e1", height=1.8, children=[base],
                              metadata={"relief_mode": "emboss"})
        text = TextNode(id="ok", text="Hello", font_size=4.0)
        svg = SVGNode(id="qr_code", file_path="qr.svg", width=24, height=24)
        doc = DocumentNode(id="doc", name="Good Card", children=[extrude, text, svg])
        analyzer = ManufacturingAnalyzer(self._profile())
        report = analyzer.analyze(doc)
        assert report.score >= 95
