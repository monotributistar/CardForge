"""SVG Visitor — renders Geometry IR nodes to SVG for 2D preview."""

from typing import Dict, List, Optional

from cardforge.geometry_ir.nodes import (
    GeometryNode, DocumentNode, GroupNode, UnionNode, DifferenceNode,
    RectangleNode, RoundedRectangleNode, SVGNode, TextNode,
    ExtrudeNode, TranslateNode, RotateNode, MirrorNode,
)
from cardforge.geometry_ir.visitor import GeometryVisitor


DEFAULT_COLORS = {
    "base": "#1a1a1a",
    "text": "#ffffff",
    "accent": "#ffd700",
    "qr": "#ffffff",
}

FACE_ORDER = {"front": 0, "back": 1}


class SVGVisitor(GeometryVisitor):
    """Renders a GeometryDocument to SVG strings.

    SVG is 2D — extrude nodes render their children,
    difference nodes show all children with reduced opacity.
    """

    def __init__(self, face_id: Optional[str] = None):
        self.face_id = face_id  # filter by face, or None for all
        self._lines: List[str] = []
        self._indent = 0
        self._width = 0.0
        self._height = 0.0

    def render(self, document: DocumentNode) -> str:
        """Render a document to an SVG string."""
        self._lines = []
        self._indent = 0

        # Scan for dimensions from base rect
        self._width, self._height = self._extract_dimensions(document)

        self._lines.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self._width}mm" height="{self._height}mm" '
            f'viewBox="0 0 {self._width} {self._height}">'
        )
        self._indent = 1
        document.accept(self)
        self._indent = 0
        self._lines.append("</svg>")
        return "\n".join(self._lines)

    def _extract_dimensions(self, document: DocumentNode) -> tuple:
        """Find card dimensions from the base rounded rect."""
        base = self._find_base_rect(document)
        if base:
            return base.width, base.height
        return 85.0, 54.0

    def _find_base_rect(self, node: GeometryNode) -> Optional[RoundedRectangleNode]:
        if isinstance(node, RoundedRectangleNode) and "card_base" in (node.id or ""):
            return node
        if hasattr(node, 'children'):
            for child in node.children:
                result = self._find_base_rect(child)
                if result:
                    return result
        return None

    def _line(self, text: str) -> None:
        prefix = "  " * self._indent
        self._lines.append(f"{prefix}{text}")

    def _color(self, node: GeometryNode) -> str:
        mat = node.metadata.get("material", "base")
        return DEFAULT_COLORS.get(mat, "#ffffff")

    def _should_render(self, node: GeometryNode) -> bool:
        if self.face_id is None:
            return True
        # Leaf nodes (shapes, text, SVG) check face metadata
        # Container nodes pass through — their children will be filtered
        if isinstance(node, (RectangleNode, RoundedRectangleNode, SVGNode, TextNode)):
            return node.metadata.get("face", "front") == self.face_id
        return True  # containers always render, children filter individually

    # ── Container visitors ──────────────────────────────────────────────

    def visit_DocumentNode(self, node: DocumentNode) -> None:
        self._visit_children(node)

    def visit_GroupNode(self, node: GroupNode) -> None:
        if not self._should_render(node):
            return
        self._visit_children(node)

    def visit_UnionNode(self, node: UnionNode) -> None:
        self._visit_children(node)

    def visit_DifferenceNode(self, node: DifferenceNode) -> None:
        # Render children with reduced opacity for diff visualization
        self._line(f'<g opacity="0.6">')
        self._indent += 1
        self._visit_children(node)
        self._indent -= 1
        self._line(f'</g>')

    # ── Shape visitors ──────────────────────────────────────────────────

    def visit_RectangleNode(self, node: RectangleNode) -> None:
        if not self._should_render(node):
            return
        color = self._color(node)
        cx = self._width / 2
        cy = self._height / 2
        x = cx - node.width / 2 if node.center else 0
        y = cy - node.height / 2 if node.center else 0
        self._line(
            f'<rect x="{x:.1f}" y="{y:.1f}" '
            f'width="{node.width}" height="{node.height}" '
            f'fill="{color}" />'
        )

    def visit_RoundedRectangleNode(self, node: RoundedRectangleNode) -> None:
        if not self._should_render(node):
            return
        color = self._color(node)
        cx = self._width / 2
        cy = self._height / 2
        x = cx - node.width / 2 if node.center else 0
        y = cy - node.height / 2 if node.center else 0
        self._line(
            f'<rect x="{x:.1f}" y="{y:.1f}" '
            f'width="{node.width}" height="{node.height}" '
            f'rx="{node.radius}" fill="{color}" />'
        )

    def visit_SVGNode(self, node: SVGNode) -> None:
        if not self._should_render(node):
            return
        href = f"../assets/{node.file_path.split('/')[-1]}"
        self._line(
            f'<image href="{href}" '
            f'width="{node.width}" height="{node.height}" '
            f'preserveAspectRatio="none" />'
        )

    def visit_TextNode(self, node: TextNode) -> None:
        if not self._should_render(node):
            return
        color = self._color(node)
        anchor_map = {"left": "start", "center": "middle", "right": "end"}
        anchor = anchor_map.get(node.halign, "start")
        self._line(
            f'<text font-family="{node.font}" font-size="{node.font_size}" '
            f'font-weight="{node.font_weight}" fill="{color}" '
            f'text-anchor="{anchor}">{node.text}</text>'
        )

    # ── Transform visitors ──────────────────────────────────────────────

    def visit_ExtrudeNode(self, node: ExtrudeNode) -> None:
        # 2D preview: just render children
        self._visit_children(node)

    def visit_TranslateNode(self, node: TranslateNode) -> None:
        if not self._should_render(node):
            return
        # Convert center-origin to top-left SVG coords
        sx = node.x + self._width / 2
        sy = self._height / 2 - node.y
        self._line(f'<g transform="translate({sx:.1f}, {sy:.1f})">')
        self._indent += 1
        self._visit_children(node)
        self._indent -= 1
        self._line(f'</g>')

    def visit_RotateNode(self, node: RotateNode) -> None:
        if not self._should_render(node):
            return
        self._line(f'<g transform="rotate({node.angle})">')
        self._indent += 1
        self._visit_children(node)
        self._indent -= 1
        self._line(f'</g>')

    def visit_MirrorNode(self, node: MirrorNode) -> None:
        if node.axis == "z":
            self._line(f'<g transform="scale(1, -1)">')
        elif node.axis == "x":
            self._line(f'<g transform="scale(-1, 1)">')
        else:
            self._line(f'<g>')
        self._indent += 1
        self._visit_children(node)
        self._indent -= 1
        self._line(f'</g>')
