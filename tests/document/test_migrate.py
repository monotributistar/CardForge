"""Tests for v1 → v2 migration — including the gate: every example migrates."""

from pathlib import Path

import pytest

from cardforge.document.migrate import detect_version, migrate_v1_to_v2
from cardforge.document.schema_v2 import DocumentV2, validate_v2

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLE_FILES = sorted(
    p for p in (PROJECT_ROOT / "examples").rglob("*.cardforge.json"))


def v1_doc():
    return {
        "document": {"id": "mini", "name": "Mini", "version": "0.1.0"},
        "manufacturing": {"profile": "fdm-standard", "process": "fdm",
                          "nozzle": 0.4, "layerHeight": 0.2, "material": "PLA"},
        "variables": {"name": "Ada"},
        "objects": [{
            "id": "main", "type": "business-card",
            "width": 85, "height": 54, "thickness": 1.8, "cornerRadius": 4,
            "theme": {"baseColor": "black", "textColor": "white", "accentColor": "gold"},
            "faces": {
                "front": {"features": [
                    {"id": "n", "type": "text-block", "position": {"x": 8, "y": 12},
                     "width": 40, "font": "Montserrat", "fontSize": 4.5,
                     "fontStyle": "bold", "align": "left",
                     "lines": ["{{name}}"],
                     "relief": {"mode": "emboss", "height": 0.4},
                     "material": "text", "zIndex": 2},
                    {"id": "pat", "type": "pattern", "patternType": "text-repeat",
                     "text": "JR", "spacing": 8, "rotation": -25,
                     "relief": {"mode": "deboss", "depth": 0.2}, "material": "base"},
                ]},
                "back": {"features": [
                    {"id": "qr", "type": "qr", "value": "https://ada.dev",
                     "position": {"x": 56, "y": 15}, "size": 24,
                     "relief": {"mode": "emboss", "height": 0.4}, "material": "text"},
                    {"id": "fr", "type": "frame", "frameStyle": "border",
                     "width": 1.2, "inset": 2.5,
                     "relief": {"mode": "emboss", "height": 0.2}, "material": "accent"},
                ]},
            },
        }],
        "exports": {"preview": True},
    }


class TestDetect:
    def test_v1_detected(self):
        assert detect_version(v1_doc()) == "1"

    def test_v2_detected(self):
        assert detect_version({"cardforge": "2.0"}) == "2"

    def test_unknown(self):
        assert detect_version({"score": 90, "files": []}) == "unknown"


class TestMigrate:
    def test_produces_valid_v2(self):
        v2 = migrate_v1_to_v2(v1_doc())
        validate_v2(v2)  # no raise

    def test_theme_becomes_palette(self):
        v2 = migrate_v1_to_v2(v1_doc())
        colors = {m["id"]: m["color"] for m in v2["materials"]}
        assert colors == {"base": "#1a1a1a", "text": "#ffffff", "accent": "#d4af37"}
        slots = {m["id"]: m["slot"] for m in v2["materials"]}
        assert slots == {"base": 1, "text": 2, "accent": 3}

    def test_dimensions_to_outline(self):
        v2 = migrate_v1_to_v2(v1_doc())
        assert v2["object"]["outline"] == {
            "type": "rounded-rect", "width": 85.0, "height": 54.0, "radius": 4.0}
        assert v2["object"]["thickness"] == 1.8

    def test_text_block_font(self):
        v2 = migrate_v1_to_v2(v1_doc())
        feat = v2["faces"]["front"]["features"][0]
        assert feat["type"] == "text-block"
        assert feat["font"] == {"family": "Montserrat", "size": 4.5, "weight": 700}
        assert feat["lines"] == ["{{name}}"]
        assert feat["zOrder"] == 2

    def test_text_repeat_pattern_becomes_text_pattern(self):
        v2 = migrate_v1_to_v2(v1_doc())
        feat = v2["faces"]["front"]["features"][1]
        assert feat["type"] == "text-pattern"
        assert feat["text"] == "JR"
        assert feat["spacing"] == 8.0
        assert feat["angle"] == -25.0
        assert feat["relief"] == {"mode": "deboss", "depth": 0.2}

    def test_qr_value_becomes_url_fields(self):
        v2 = migrate_v1_to_v2(v1_doc())
        feat = v2["faces"]["back"]["features"][0]
        assert feat["type"] == "qr"
        assert feat["qrType"] == "url"
        assert feat["fields"] == {"url": "https://ada.dev"}
        assert feat["size"] == 24.0

    def test_frame_becomes_shape(self):
        v2 = migrate_v1_to_v2(v1_doc())
        feat = v2["faces"]["back"]["features"][1]
        assert feat["type"] == "shape"
        assert feat["shapeType"] == "frame"
        assert feat["strokeWidth"] == 1.2
        assert feat["inset"] == 2.5

    def test_positions_preserved(self):
        v2 = migrate_v1_to_v2(v1_doc())
        assert v2["faces"]["front"]["features"][0]["transform"] == {"x": 8.0, "y": 12.0}


class TestMigrationGate:
    """The Phase 1 gate: every shipped example must migrate, validate, load."""

    @pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.name)
    def test_example_migrates_and_loads(self, path):
        import json

        data = json.loads(path.read_text())
        assert detect_version(data) == "1", f"{path.name} should be a v1 document"
        v2 = migrate_v1_to_v2(data)
        model = DocumentV2.from_dict(v2)  # validates
        assert model.materials, "palette must not be empty"
        assert model.faces, "faces must survive migration"
        total_features = sum(len(f.features) for f in model.faces.values())
        assert total_features > 0, "features must survive migration"

    def test_loader_transparently_migrates(self):
        from cardforge.document.loader import load_document_v2

        example = EXAMPLE_FILES[0]
        model = load_document_v2(str(example))
        assert isinstance(model, DocumentV2)
