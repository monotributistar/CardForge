"""Geometry Builder — converts Card Domain Model into Geometry IR."""

from pathlib import Path
from typing import Optional

from cardforge.domain.card import Card
from cardforge.domain.feature import (
    Feature, TextBlockFeature, QRCodeFeature, PatternFeature,
    LogoFeature, FrameFeature, CornerDecorationFeature,
)
from cardforge.domain.geometry import ReliefMode
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.geometry_ir.nodes import (
    DocumentNode, GroupNode, UnionNode, DifferenceNode,
    RectangleNode, RoundedRectangleNode, SVGNode, TextNode,
    ExtrudeNode, TranslateNode, MirrorNode, GeometryNode,
)


class GeometryBuilder:
    """Builds a GeometryDocument from a Card domain object.

    Usage:
        builder = GeometryBuilder()
        document = builder.build(card, generated_assets)
    """

    def build(
        self,
        card: Card,
        generated_assets: Optional[GeneratedAssets] = None,
    ) -> DocumentNode:
        """Convert a Card into a GeometryDocument.

        Args:
            card: Populated Card domain object.
            generated_assets: Generated QR/pattern assets for SVG references.

        Returns:
            A DocumentNode representing the complete geometry tree.
        """
        doc = DocumentNode(
            id=card.id,
            name=card.name,
            metadata={"object_type": card.object_type},
        )

        # Build asset lookups
        qr_map = {}
        pattern_map = {}
        if generated_assets:
            qr_map = {p.stem: str(p) for p in generated_assets.qr_paths}
            pattern_map = {p.stem: str(p) for p in generated_assets.pattern_paths}

        # ── Base card body ────────────────────────────────────────────────
        root_union = UnionNode(id="card_body")

        # Card base shape
        base = self._build_card_base(card)
        root_union.add_child(base)

        # ── Front face features ───────────────────────────────────────────
        front = card.get_face("front")
        if front:
            front_group = self._build_face_features(
                card, front, "front", qr_map, pattern_map, is_back=False,
            )
            if front_group.children:
                root_union.add_child(front_group)

        # ── Back face features ────────────────────────────────────────────
        back = card.get_face("back")
        if back:
            back_group = self._build_face_features(
                card, back, "back", qr_map, pattern_map, is_back=True,
            )
            if back_group.children:
                root_union.add_child(back_group)

        doc.add_child(root_union)
        return doc

    def _build_card_base(self, card: Card) -> ExtrudeNode:
        """Build the card base as an extruded rounded rectangle."""
        rect = RoundedRectangleNode(
            id="card_base",
            width=card.width,
            height=card.height,
            radius=card.corner_radius,
            metadata={"material": "base"},
        )
        return ExtrudeNode(
            id="card_base_extrude",
            height=card.thickness,
            children=[rect],
            metadata={"material": "base"},
        )

    def _build_face_features(
        self,
        card: Card,
        face,
        face_id: str,
        qr_map: dict,
        pattern_map: dict,
        is_back: bool,
    ) -> GroupNode:
        """Build a group for all features on a face."""
        group = GroupNode(id=f"face_{face_id}")
        half_w = card.width / 2
        half_h = card.height / 2
        thickness = card.thickness

        for feature in face.sorted_features():
            if not feature.visible:
                continue

            node = self._build_feature_node(
                card, feature, face_id, half_w, half_h, thickness,
                qr_map, pattern_map,
            )
            if node:
                group.add_child(node)

        if is_back:
            # Wrap in mirror for back face
            mirror = MirrorNode(id=f"mirror_{face_id}", axis="z", children=[group])
            return GroupNode(id=f"face_{face_id}_wrapped", children=[mirror])

        return group

    def _build_feature_node(
        self,
        card: Card,
        feature: Feature,
        face_id: str,
        half_w: float,
        half_h: float,
        thickness: float,
        qr_map: dict,
        pattern_map: dict,
    ) -> Optional[GeometryNode]:
        """Build a geometry node for a single feature."""
        scad_x = feature.position.x - half_w
        scad_y = half_h - feature.position.y
        relief = feature.relief
        mode = relief.mode
        z_pos = thickness
        meta = {
            "source_feature": feature.id,
            "material": feature.material.id if feature.material else "base",
            "face": face_id,
        }

        if isinstance(feature, QRCodeFeature):
            stem = f"qr_{feature.id}"
            if stem in qr_map:
                qr_size = feature.size.width or 24
                cx = scad_x + qr_size / 2
                cy = scad_y - qr_size / 2
                height_val = relief.height if mode == ReliefMode.EMBOSS else 0.4
                svg = SVGNode(
                    id=f"qr_{feature.id}",
                    file_path=qr_map[stem],
                    width=qr_size,
                    height=qr_size,
                    metadata=meta,
                )
                extruded = ExtrudeNode(
                    id=f"qr_extrude_{feature.id}",
                    height=height_val,
                    children=[svg],
                    metadata=meta,
                )
                return TranslateNode(
                    id=f"qr_translate_{feature.id}",
                    x=cx, y=cy, z=z_pos,
                    children=[extruded],
                    metadata=meta,
                )

        elif isinstance(feature, PatternFeature):
            stem = f"pattern_{face_id}_{feature.id}"
            if stem in pattern_map:
                if mode == ReliefMode.DEBOSS:
                    depth_val = relief.depth or 0.2
                    svg = SVGNode(
                        id=f"pattern_{feature.id}",
                        file_path=pattern_map[stem],
                        width=card.width,
                        height=card.height,
                        metadata=meta,
                    )
                    extruded = ExtrudeNode(
                        id=f"pattern_deboss_{feature.id}",
                        height=depth_val,
                        children=[svg],
                        metadata=meta,
                    )
                    return TranslateNode(
                        id=f"pattern_translate_{feature.id}",
                        x=0, y=0, z=thickness - depth_val,
                        children=[extruded],
                        metadata=meta,
                    )
                else:
                    height_val = relief.height if mode == ReliefMode.EMBOSS else 0.2
                    svg = SVGNode(
                        id=f"pattern_{feature.id}",
                        file_path=pattern_map[stem],
                        width=card.width,
                        height=card.height,
                        metadata=meta,
                    )
                    extruded = ExtrudeNode(
                        id=f"pattern_extrude_{feature.id}",
                        height=height_val,
                        children=[svg],
                        metadata=meta,
                    )
                    return TranslateNode(
                        id=f"pattern_translate_{feature.id}",
                        x=0, y=0, z=thickness,
                        children=[extruded],
                        metadata=meta,
                    )

        elif isinstance(feature, TextBlockFeature):
            height_val = relief.height if mode == ReliefMode.EMBOSS else 0.4
            text_group = GroupNode(id=f"text_group_{feature.id}", metadata=meta)
            for i, line in enumerate(feature.lines):
                ly = scad_y - i * feature.font_size * feature.line_height
                text_node = TextNode(
                    id=f"text_{feature.id}_{i}",
                    text=line,
                    font=feature.font,
                    font_size=feature.font_size,
                    font_weight=feature.font_style,
                    halign=feature.align,
                    metadata=meta,
                )
                extruded = ExtrudeNode(
                    id=f"text_extrude_{feature.id}_{i}",
                    height=height_val,
                    children=[text_node],
                    metadata=meta,
                )
                translated = TranslateNode(
                    id=f"text_translate_{feature.id}_{i}",
                    x=scad_x, y=ly, z=z_pos,
                    children=[extruded],
                    metadata=meta,
                )
                text_group.add_child(translated)
            return text_group

        elif isinstance(feature, LogoFeature):
            logo_w = feature.size.width or 20
            logo_h = feature.size.height or 20
            height_val = relief.height if mode == ReliefMode.EMBOSS else 0.5
            rect = RectangleNode(
                id=f"logo_rect_{feature.id}",
                width=logo_w,
                height=logo_h,
                metadata=meta,
            )
            extruded = ExtrudeNode(
                id=f"logo_extrude_{feature.id}",
                height=height_val,
                children=[rect],
                metadata=meta,
            )
            return TranslateNode(
                id=f"logo_translate_{feature.id}",
                x=scad_x, y=scad_y, z=z_pos,
                children=[extruded],
                metadata=meta,
            )

        return None
