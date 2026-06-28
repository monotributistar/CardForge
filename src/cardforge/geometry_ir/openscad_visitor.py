"""OpenSCAD Visitor — renders Geometry IR nodes to OpenSCAD code."""

from pathlib import Path
from typing import List

from cardforge.geometry_ir.nodes import (
    GeometryNode, DocumentNode, GroupNode, UnionNode, DifferenceNode,
    RectangleNode, RoundedRectangleNode, SVGNode, TextNode,
    ExtrudeNode, TranslateNode, MirrorNode,
)
from cardforge.geometry_ir.visitor import GeometryVisitor
from cardforge.scad.writer import ScadWriter
from cardforge.scad.expressions import number, vector3, escape_string


class OpenSCADVisitor(GeometryVisitor):
    """Converts a Geometry IR document tree into OpenSCAD source code."""

    def __init__(self, openscad_dir: Path = None):
        self.writer = ScadWriter()
        self._openscad_dir = openscad_dir or Path("openscad")

    def render(self, document: DocumentNode) -> str:
        """Render a document to an OpenSCAD string."""
        self.writer = ScadWriter()
        self.writer.comment("CardForge — Auto-generated OpenSCAD (via Geometry IR)")
        self.writer.comment(f"Project: {document.name}")
        self.writer.comment("Do not edit manually — edit config JSON instead")
        self.writer.blank_line()

        # Include modules
        main_scad = self._openscad_dir / "main.scad"
        self.writer.include(str(main_scad.resolve()))
        self.writer.blank_line()

        # Visit document
        document.accept(self)

        return self.writer.build()

    # ── Container nodes ──────────────────────────────────────────────────

    def visit_DocumentNode(self, node: DocumentNode) -> None:
        self._visit_children(node)

    def visit_GroupNode(self, node: GroupNode) -> None:
        self._visit_children(node)

    def visit_UnionNode(self, node: UnionNode) -> None:
        if len(node.children) == 1:
            self._visit_children(node)
        else:
            self.writer.open_block("union()")
            self._visit_children(node)
            self.writer.close_block()

    def visit_DifferenceNode(self, node: DifferenceNode) -> None:
        self.writer.open_block("difference()")
        self._visit_children(node)
        self.writer.close_block()

    # ── Shape nodes ──────────────────────────────────────────────────────

    def visit_RectangleNode(self, node: RectangleNode) -> None:
        if node.center:
            self.writer.module_call(
                "square",
                size=(node.width, node.height),
                center=True,
            )
        else:
            self.writer.line(
                f"square([{number(node.width)}, {number(node.height)}]);"
            )

    def visit_RoundedRectangleNode(self, node: RoundedRectangleNode) -> None:
        self.writer.module_call(
            "rounded_rect_2d",
            width=node.width,
            height=node.height,
            radius=node.radius,
        )

    def visit_SVGNode(self, node: SVGNode) -> None:
        # For center=true imports, scale so 1-unit = svg native size
        self.writer.module_call(
            "svg_emboss_layer",
            file=node.file_path,
            x=0, y=0, z=0,
            height=1,
            scale_factor=node.width,
        )

    def visit_TextNode(self, node: TextNode) -> None:
        self.writer.module_call(
            "text_emboss_layer",
            text_value=node.text,
            x=0, y=0, z=0,
            font_size=node.font_size,
            height=1,
            font_name=node.font,
            halign=node.halign,
            valign=node.valign,
        )

    # ── 3D / Transform nodes ─────────────────────────────────────────────

    def visit_ExtrudeNode(self, node: ExtrudeNode) -> None:
        center_arg = "true" if node.center else "false"
        self.writer.open_block(
            f"linear_extrude(height={number(node.height)}, center={center_arg})"
        )
        self._visit_children(node)
        self.writer.close_block()

    def visit_TranslateNode(self, node: TranslateNode) -> None:
        self.writer.open_block(
            f"translate({vector3(node.x, node.y, node.z)})"
        )
        self._visit_children(node)
        self.writer.close_block()

    def visit_MirrorNode(self, node: MirrorNode) -> None:
        axis_map = {"x": "[1, 0, 0]", "y": "[0, 1, 0]", "z": "[0, 0, 1]"}
        ax = axis_map.get(node.axis, "[0, 0, 1]")
        self.writer.open_block(f"mirror({ax})")
        self._visit_children(node)
        self.writer.close_block()
