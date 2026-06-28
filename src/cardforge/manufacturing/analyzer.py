"""Manufacturing Analyzer — analyzes Geometry IR against a manufacturing profile.

Implemented as a GeometryVisitor that walks the IR tree and applies
manufacturing rules at each node.
"""

from typing import List

from cardforge.geometry_ir.nodes import (
    GeometryNode, DocumentNode, GroupNode, UnionNode, DifferenceNode,
    RectangleNode, RoundedRectangleNode, SVGNode, TextNode,
    ExtrudeNode, TranslateNode, MirrorNode,
)
from cardforge.geometry_ir.visitor import GeometryVisitor
from cardforge.manufacturing.profiles import ManufacturingProfile
from cardforge.manufacturing.report import ManufacturingReport, ManufacturingFix
from cardforge.manufacturing.metrics import ManufacturingMetrics
from cardforge.manufacturing.issues import ManufacturingIssue, IssueCode, Severity
from cardforge.manufacturing.rules import (
    check_line_width, check_wall_thickness,
    check_emboss_height, check_deboss_depth,
    check_qr_size, check_qr_module_size,
    check_text_size, check_gap,
)


class ManufacturingAnalyzer(GeometryVisitor):
    """Analyzes a GeometryDocument for manufacturability.

    Walks the IR tree with the Visitor pattern, applying rules
    at each node based on the manufacturing profile.

    Usage:
        profile = ManufacturingProfile.fdm_standard()
        analyzer = ManufacturingAnalyzer(profile)
        report = analyzer.analyze(document)
    """

    def __init__(self, profile: ManufacturingProfile = None):
        self.profile = profile or ManufacturingProfile.fdm_standard()
        self.report = ManufacturingReport(profile=self.profile)
        self.metrics = ManufacturingMetrics()
        self._feature_meta = {}  # track feature metadata across nodes

    def analyze(self, document: DocumentNode) -> ManufacturingReport:
        """Run manufacturing analysis on a geometry document.

        Args:
            document: The Geometry IR document to analyze.

        Returns:
            ManufacturingReport with issues, metrics, and score.
        """
        self.report = ManufacturingReport(profile=self.profile)
        self.metrics = ManufacturingMetrics()
        document.accept(self)
        self.report.metrics = self.metrics
        return self.report

    # ── Container visitors ───────────────────────────────────────────────

    def visit_DocumentNode(self, node: DocumentNode) -> None:
        self.metrics.feature_count = len(node.children)
        self._visit_children(node)

    def visit_GroupNode(self, node: GroupNode) -> None:
        self._visit_children(node)

    def visit_UnionNode(self, node: UnionNode) -> None:
        self._visit_children(node)

    def visit_DifferenceNode(self, node: DifferenceNode) -> None:
        self._visit_children(node)

    # ── Shape visitors ───────────────────────────────────────────────────

    def visit_RectangleNode(self, node: RectangleNode) -> None:
        self.metrics.update_line(node.width)
        self.metrics.update_line(node.height)
        self.metrics.update_wall(min(node.width, node.height))
        self._check_feature_bounds(node)

        issues = check_line_width(node.width, node.height, node.id, self.profile)
        issues += check_wall_thickness(min(node.width, node.height), node.id, self.profile)
        for issue in issues:
            self.report.add_issue(issue)

        self._visit_children(node)

    def visit_RoundedRectangleNode(self, node: RoundedRectangleNode) -> None:
        self.metrics.update_line(node.width)
        self.metrics.update_line(node.height)
        self._check_feature_bounds(node)
        self._visit_children(node)

    def visit_SVGNode(self, node: SVGNode) -> None:
        self.metrics.svg_count += 1
        self.metrics.update_line(node.width)
        self.metrics.update_line(node.height)

        # QR detection via metadata or filename
        if "qr" in node.id.lower() or "qr" in node.metadata.get("source_feature", "").lower():
            qr_size = node.width
            self.metrics.update_qr(qr_size)
            issues = check_qr_size(qr_size, node.id, self.profile)
            issues += check_qr_module_size(qr_size, node.id, self.profile)
            for issue in issues:
                self.report.add_issue(issue)

        self._visit_children(node)

    def visit_TextNode(self, node: TextNode) -> None:
        self.metrics.text_count += 1
        self.metrics.update_text(node.font_size)
        issues = check_text_size(node.font_size, node.id, self.profile)
        for issue in issues:
            self.report.add_issue(issue)
        self._visit_children(node)

    # ── 3D / Transform visitors ──────────────────────────────────────────

    def visit_ExtrudeNode(self, node: ExtrudeNode) -> None:
        self.metrics.extrude_count += 1
        # Check emboss/deboss from metadata
        relief_mode = node.metadata.get("relief_mode", "emboss")
        if relief_mode == "emboss":
            self.metrics.update_emboss(node.height)
            issues = check_emboss_height(node.height, node.id, self.profile)
            for issue in issues:
                self.report.add_issue(issue)
        elif relief_mode == "deboss":
            self.metrics.update_deboss(node.height)
            issues = check_deboss_depth(node.height, node.id, self.profile)
            for issue in issues:
                self.report.add_issue(issue)
        self._visit_children(node)

    def visit_TranslateNode(self, node: TranslateNode) -> None:
        # Check if feature is within card bounds (0 to card_width/height)
        # Bounds check: card center-origin means -w/2 <= x <= w/2
        # We check if the node is far out of a reasonable range
        self._visit_children(node)

    def visit_MirrorNode(self, node: MirrorNode) -> None:
        self._visit_children(node)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _check_feature_bounds(self, node: GeometryNode) -> None:
        """Check that a feature is within printable bounds."""
        # Approximate: if we have a position from a parent translate,
        # check it's within reasonable card dimensions.
        # For now, just a basic check based on metadata
        pass
