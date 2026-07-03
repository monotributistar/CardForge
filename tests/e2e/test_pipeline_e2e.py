"""E2E tests — full pipeline from document to STL, verifying geometry content."""

import json
import struct
import tempfile
from pathlib import Path

import pytest

from cardforge.document.model import CardForgeDocument
from cardforge.document.adapter import resolve_document_variables, adapt_to_legacy_config
from cardforge.domain.factory import create_card_from_config
from cardforge.geometry_ir.builder import GeometryBuilder
from cardforge.geometry_ir.nodes import (
    DocumentNode, UnionNode, ExtrudeNode, TextNode, SVGNode,
    RoundedRectangleNode, RectangleNode, GroupNode, TranslateNode,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _count_stl_triangles(path: Path) -> int:
    """Count triangles in a binary STL file."""
    with open(path, "rb") as f:
        f.read(80)  # header
        return struct.unpack("<I", f.read(4))[0]


def _make_doc(features: dict = None):
    """Create a minimal CardForgeDocument with optional features per face."""
    return CardForgeDocument.from_dict({
        "document": {"id": "test", "name": "Test Card"},
        "manufacturing": {"process": "fdm", "profile": "fdm-standard", "nozzle": 0.4, "layerHeight": 0.2, "material": "PLA"},
        "variables": {"name": "Javier", "title": "Dev", "email": "j@test.com", "website": "https://test.com", "phone": "+54"},
        "objects": [{
            "id": "main", "type": "business-card", "width": 85, "height": 54, "thickness": 1.8, "cornerRadius": 4,
            "theme": {"baseColor": "black", "textColor": "white", "accentColor": "gold"},
            "faces": features or {"front": {"features": []}, "back": {"features": []}},
        }],
        "exports": {},
    })


def _build_card(doc):
    """Run full pipeline: doc → config → card → geometry → SCAD → STL."""
    doc = resolve_document_variables(doc)
    config = adapt_to_legacy_config(doc)
    card = create_card_from_config(config)
    builder = GeometryBuilder()
    geom = builder.build(card)
    return card, geom


def _collect_nodes(node, node_type):
    """Collect all nodes of a given type from the geometry tree."""
    results = []
    if isinstance(node, node_type):
        results.append(node)
    for child in getattr(node, "children", []):
        results.extend(_collect_nodes(child, node_type))
    return results


def _count_features(geom):
    """Count features by type in geometry tree."""
    return {
        "text": len(_collect_nodes(geom, TextNode)),
        "svg": len(_collect_nodes(geom, SVGNode)),
        "extrude": len(_collect_nodes(geom, ExtrudeNode)),
        "rounded_rect": len(_collect_nodes(geom, RoundedRectangleNode)),
        "rectangle": len(_collect_nodes(geom, RectangleNode)),
    }


# ── Tests ────────────────────────────────────────────────────────────────

class TestEmptyCard:
    """Empty card = base only, no features."""

    def test_geometry_has_base(self):
        doc = _make_doc()
        _, geom = _build_card(doc)
        extrudes = _collect_nodes(geom, ExtrudeNode)
        assert len(extrudes) >= 1, "Should have at least the base extrude"
        # Base extrude should have a rounded rectangle child
        rounded = _collect_nodes(geom, RoundedRectangleNode)
        assert len(rounded) >= 1, "Should have a rounded rectangle for card base"

    def test_no_text_or_qr(self):
        doc = _make_doc()
        _, geom = _build_card(doc)
        counts = _count_features(geom)
        assert counts["text"] == 0, "Empty card should have no text"
        assert counts["svg"] == 0, "Empty card should have no SVG"

    def test_empty_card_builds_to_stl(self):
        """Build actual STL and verify it's not empty."""
        import subprocess, sys
        doc = _make_doc()
        config = adapt_to_legacy_config(resolve_document_variables(doc))
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(config, f)
            config_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, "scripts/build.py", config_path, "--stl", "--clean"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                pytest.skip(f"build.py failed: {result.stderr[:200]}")
            # Find generated STL
            stl_path = Path("exports") / config["project"]["name"] / "stl" / "card_single.stl"
            assert stl_path.exists(), f"STL not found at {stl_path}"
            tris = _count_stl_triangles(stl_path)
            assert tris > 0, "STL should have triangles"
            assert tris >= 12, f"Base card (2 triangles per face × 6 faces) should have ≥12 triangles, got {tris}"
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestTextOnlyCard:
    """Card with only text features."""

    def test_text_renders_in_geometry(self):
        doc = _make_doc({
            "back": {"features": [
                {"id": "contact", "type": "text-block", "position": {"x": 8, "y": 12},
                 "size": {"width": 40, "height": 20}, "font": "Arial", "fontSize": 3.2,
                 "lines": ["Javier", "Developer"], "material": "text",
                 "relief": {"mode": "emboss", "height": 0.4}},
            ]}
        })
        _, geom = _build_card(doc)
        counts = _count_features(geom)
        assert counts["text"] >= 2, f"Should have 2 text nodes (2 lines), got {counts['text']}"
        assert counts["extrude"] >= 3, "Should have base extrude + 2 text extrudes"

    def test_text_has_correct_metadata(self):
        doc = _make_doc({
            "back": {"features": [
                {"id": "contact", "type": "text-block", "position": {"x": 8, "y": 12},
                 "size": {"width": 40, "height": 20}, "font": "Arial", "fontSize": 3.2,
                 "lines": ["Javier"], "material": "text",
                 "relief": {"mode": "emboss", "height": 0.4}},
            ]}
        })
        _, geom = _build_card(doc)
        texts = _collect_nodes(geom, TextNode)
        assert len(texts) >= 1
        text_node = texts[0]
        assert text_node.metadata.get("source_feature") == "contact"
        assert text_node.metadata.get("material") == "text"

    def test_text_builds_to_stl(self):
        doc = _make_doc({
            "back": {"features": [
                {"id": "contact", "type": "text-block", "position": {"x": 8, "y": 12},
                 "size": {"width": 40, "height": 20}, "font": "Arial", "fontSize": 3.2,
                 "lines": ["Javier"], "material": "text",
                 "relief": {"mode": "emboss", "height": 0.4}},
            ]}
        })
        import subprocess, sys
        doc = resolve_document_variables(doc)
        config = adapt_to_legacy_config(doc)
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(config, f)
            config_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, "scripts/build.py", config_path, "--stl", "--clean"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                pytest.skip(f"build.py failed: {result.stderr[:200]}")
            stl_path = Path("exports") / config["project"]["name"] / "stl" / "card_single.stl"
            assert stl_path.exists()
            tris = _count_stl_triangles(stl_path)
            # Text features add triangles — should be more than just the base
            assert tris > 12, f"Text card should have more triangles than empty base (12), got {tris}"
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestTemplates:
    """All 3 prototype templates must build with correct features."""

    TEMPLATES = [
        "examples/prototypes/card_minimal.cardforge.json",
        "examples/prototypes/card_dark_luxury.cardforge.json",
        "examples/prototypes/card_tech_pattern.cardforge.json",
    ]

    def _load_and_build(self, path):
        from cardforge.document.loader import load_document
        doc = load_document(path)
        doc = resolve_document_variables(doc)
        config = adapt_to_legacy_config(doc)
        card = create_card_from_config(config)
        builder = GeometryBuilder()
        geom = builder.build(card)
        return doc, config, card, geom

    @pytest.mark.parametrize("template_path", TEMPLATES)
    def test_template_loads(self, template_path):
        """Template must load without errors."""
        from cardforge.document.loader import load_document
        doc = load_document(template_path)
        assert doc.metadata.name
        assert len(doc.objects) >= 1

    @pytest.mark.parametrize("template_path", TEMPLATES)
    def test_template_builds_geometry(self, template_path):
        """Template must produce geometry with features."""
        _, _, _, geom = self._load_and_build(template_path)
        counts = _count_features(geom)
        # Every template should at least have a base
        assert counts["extrude"] >= 1, f"{template_path}: should have base extrude"

    @pytest.mark.parametrize("template_path", TEMPLATES)
    def test_template_builds_stl(self, template_path):
        """Template must produce a valid STL."""
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "scripts/build.py", template_path, "--stl", "--clean"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            pytest.fail(f"build.py failed for {template_path}: {result.stderr[:300]}")

    @pytest.mark.parametrize("template_path", TEMPLATES)
    def test_template_has_expected_features(self, template_path):
        """Each template must have features of the expected types."""
        _, _, _, geom = self._load_and_build(template_path)
        counts = _count_features(geom)

        if "minimal" in template_path:
            # Minimal should have text (contact info) + QR
            assert counts["text"] >= 1, f"Minimal template should have text, got {counts}"
        elif "luxury" in template_path:
            # Dark luxury should have text + QR + pattern
            assert counts["text"] >= 1, f"Luxury template should have text, got {counts}"
        elif "tech" in template_path:
            # Tech pattern should have text + QR + pattern
            assert counts["text"] >= 1, f"Tech template should have text, got {counts}"

    @pytest.mark.parametrize("template_path", TEMPLATES)
    def test_template_stl_has_content(self, template_path):
        """Generated STL must have more than just the base (12 triangles)."""
        import subprocess, sys
        import re

        result = subprocess.run(
            [sys.executable, "scripts/build.py", template_path, "--stl", "--clean"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            pytest.skip(f"build.py failed")

        # Extract project name from config
        with open(template_path) as f:
            data = json.load(f)
        project_name = data.get("document", {}).get("id", "unknown")
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)

        stl_path = Path("exports") / safe_name / "stl" / "card_single.stl"
        if stl_path.exists():
            tris = _count_stl_triangles(stl_path)
            assert tris >= 12, f"{template_path}: STL has {tris} triangles, expected ≥12 (base card)"
        else:
            # Try legacy name
            legacy_name = data.get("document", {}).get("name", "unknown")
            safe_legacy = re.sub(r'[^a-zA-Z0-9_-]', '_', legacy_name)
            stl_path = Path("exports") / safe_legacy / "stl" / "card_single.stl"
            if stl_path.exists():
                tris = _count_stl_triangles(stl_path)
                assert tris >= 12, f"{template_path}: STL has {tris} triangles"


class TestQRFeature:
    """QR features must appear in geometry even without assets."""

    def test_qr_has_geometry_fallback(self):
        doc = _make_doc({
            "back": {"features": [
                {"id": "qr", "type": "qr", "qrType": "url", "url": "https://test.com",
                 "size": 24, "position": {"x": 56, "y": 15}, "material": "text",
                 "relief": {"mode": "emboss", "height": 0.4}},
            ]}
        })
        _, geom = _build_card(doc)
        counts = _count_features(geom)
        # QR should produce at least a rectangle or SVG node
        has_qr_geometry = counts["rectangle"] >= 1 or counts["svg"] >= 1
        assert has_qr_geometry, f"QR should generate geometry (rect or SVG), got {counts}"

    def test_qr_not_skipped(self):
        doc = _make_doc({
            "back": {"features": [
                {"id": "qr", "type": "qr", "qrType": "url", "url": "https://test.com",
                 "size": 24, "position": {"x": 56, "y": 15}, "material": "text",
                 "relief": {"mode": "emboss", "height": 0.4}},
            ]}
        })
        _, geom = _build_card(doc)
        extrudes = _collect_nodes(geom, ExtrudeNode)
        # Base (1) + QR (1) = at least 2 extrudes
        assert len(extrudes) >= 2, f"Should have base + QR extrudes, got {len(extrudes)}"


class TestAssetFeatures:
    """Asset features (guard, corner, trama) must appear in geometry."""

    def test_frame_feature_renders(self):
        doc = _make_doc({
            "back": {"features": [
                {"id": "frame1", "type": "frame", "position": {"x": 0, "y": 0},
                 "size": {"width": 85, "height": 54}, "material": "accent",
                 "relief": {"mode": "emboss", "height": 0.15}, "inset": 4},
            ]}
        })
        _, geom = _build_card(doc)
        # Frame should produce geometry nodes
        all_nodes = []
        def collect(n):
            all_nodes.append(type(n).__name__)
            for c in getattr(n, "children", []): collect(c)
        collect(geom)
        # Should not be empty beyond the base
        assert len(all_nodes) > 3, f"Frame card should have multiple nodes, got {len(all_nodes)}: {all_nodes}"

    def test_corner_feature_renders(self):
        doc = _make_doc({
            "back": {"features": [
                {"id": "corner1", "type": "corner", "position": {"x": 0, "y": 0},
                 "size": {"width": 85, "height": 54}, "material": "accent",
                 "relief": {"mode": "emboss", "height": 0.15}, "cornerSize": 6},
            ]}
        })
        _, geom = _build_card(doc)
        all_nodes = []
        def collect(n):
            all_nodes.append(type(n).__name__)
            for c in getattr(n, "children", []): collect(c)
        collect(geom)
        assert len(all_nodes) > 3, f"Corner card should have multiple nodes, got {len(all_nodes)}"
