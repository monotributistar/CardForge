"""Asset Manager — generates derived assets (QR, patterns) from a Card."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cardforge.domain.card import Card
from cardforge.domain.feature import QRCodeFeature, PatternFeature
from cardforge.assets.qr import generate_qr_svg
from cardforge.assets.vcard import build_vcard
from cardforge.assets.patterns import generate_text_repeat_pattern_svg
from cardforge.export.paths import ExportPaths


@dataclass
class GeneratedAssets:
    """Tracks paths to all generated assets."""

    qr_paths: List[Path] = field(default_factory=list)
    pattern_paths: List[Path] = field(default_factory=list)
    logo_paths: List[Path] = field(default_factory=list)

    @property
    def all_paths(self) -> List[Path]:
        return self.qr_paths + self.pattern_paths + self.logo_paths


def generate_assets(
    card: Card,
    config: dict,
    export_paths: ExportPaths,
) -> GeneratedAssets:
    """Generate all derived assets from a Card domain object.

    Args:
        card: Populated Card domain object.
        config: Original resolved config (for owner data, etc.).
        export_paths: Organized export directory paths.

    Returns:
        GeneratedAssets tracking all created files.
    """
    assets = GeneratedAssets()

    owner = config.get("owner", {})

    for feature in card.all_features():
        if isinstance(feature, QRCodeFeature):
            # Build QR value based on type
            if feature.qr_type == "vcard":
                qr_value = build_vcard(owner)
            elif feature.qr_type == "url":
                qr_value = owner.get("website", "")
            else:
                qr_value = owner.get("name", "CardForge")

            if qr_value:
                qr_path = export_paths.assets_dir / f"qr_{feature.id}.svg"
                generate_qr_svg(
                    qr_value,
                    qr_path,
                    size_mm=feature.size.width or 24,
                    quiet_zone_mm=feature.quiet_zone,
                    error_correction=feature.error_correction,
                )
                assets.qr_paths.append(qr_path)

        elif isinstance(feature, PatternFeature):
            if feature.pattern_type == "text-repeat":
                pattern_path = export_paths.assets_dir / f"pattern_{feature.face}_{feature.id}.svg"
                generate_text_repeat_pattern_svg(
                    feature.text or "CF",
                    pattern_path,
                    width_mm=card.width,
                    height_mm=card.height,
                    spacing_mm=feature.spacing,
                    rotation_deg=feature.rotation_degrees,
                )
                assets.pattern_paths.append(pattern_path)

    return assets
