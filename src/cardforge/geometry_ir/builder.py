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
        material_filter: Optional[str] = None,
    ) -> DocumentNode:
        """Convert a Card into a GeometryDocument.

        Args:
            card: Populated Card domain object.
            generated_assets: Generated QR/pattern assets for SVG references.
            material_filter: If set, only include geometry for this material id.
                The card body (base) is included only when the filter is None or
                equals "base". Used to produce one STL per material.

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

        # Card base shape — only in the unfiltered doc or the "base" material.
        if material_filter is None or material_filter == "base":
            base = self._build_card_base(card)
            root_union.add_child(base)

        # ── Front face features ───────────────────────────────────────────
        front = card.get_face("front")
        if front:
            front_group = self._build_face_features(
                card, front, "front", qr_map, pattern_map, is_back=False,
                material_filter=material_filter,
            )
            if front_group.children:
                root_union.add_child(front_group)

        # ── Back face features ────────────────────────────────────────────
        back = card.get_face("back")
        if back:
            back_group = self._build_face_features(
                card, back, "back", qr_map, pattern_map, is_back=True,
                material_filter=material_filter,
            )
            if back_group.children:
                root_union.add_child(back_group)

        doc.add_child(root_union)
        return doc

    @staticmethod
    def _feature_material(feature: Feature) -> str:
        """Material id a feature belongs to (defaults to 'base')."""
        return feature.material.id if feature.material else "base"

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
        material_filter: Optional[str] = None,
    ) -> GroupNode:
        """Build a group for all features on a face."""
        group = GroupNode(id=f"face_{face_id}")
        half_w = card.width / 2
        half_h = card.height / 2
        thickness = card.thickness

        # Features are always extruded "upward" from the surface they sit on.
        # The back face is wrapped in mirror([0,0,1]) below, so its features are
        # built against z=0 (extrude 0..h → mirrored to -h..0, flush on the
        # bottom face). Front features sit on the top surface (z=thickness).
        # Using z=thickness for the back too would place them at -(thickness+h),
        # detached ~thickness mm below the card.
        z_surface = 0.0 if is_back else thickness

        for feature in face.sorted_features():
            if not feature.visible:
                continue

            if material_filter is not None and self._feature_material(feature) != material_filter:
                continue

            node = self._build_feature_node(
                card, feature, face_id, half_w, half_h, thickness,
                qr_map, pattern_map, z_surface,
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
        z_surface: Optional[float] = None,
    ) -> Optional[GeometryNode]:
        """Build a geometry node for a single feature.

        z_surface is the z the feature sits on before any face mirror
        (thickness for the front, 0 for the back). Defaults to thickness.
        """
        scad_x = feature.position.x - half_w
        scad_y = half_h - feature.position.y
        relief = feature.relief
        mode = relief.mode
        if z_surface is None:
            z_surface = thickness
        z_pos = z_surface
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
            else:
                # No asset available — generate placeholder geometry
                qr_size = feature.size.width or 24
                height_val = relief.height if mode == ReliefMode.EMBOSS else 0.4
                rect = RectangleNode(
                    id=f"qr_rect_{feature.id}",
                    width=qr_size,
                    height=qr_size,
                    metadata=meta,
                )
                extruded = ExtrudeNode(
                    id=f"qr_extrude_{feature.id}",
                    height=height_val,
                    children=[rect],
                    metadata=meta,
                )
                return TranslateNode(
                    id=f"qr_translate_{feature.id}",
                    x=scad_x, y=scad_y - qr_size, z=z_pos,
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
                        x=0, y=0, z=z_surface - depth_val,
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
                        x=0, y=0, z=z_surface,
                        children=[extruded],
                        metadata=meta,
                    )
            else:
                # No asset — return empty group (don't skip feature)
                return GroupNode(id=f"pattern_empty_{feature.id}", metadata=meta)

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
