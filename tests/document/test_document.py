"""Tests for document model, loader, adapter, and prototype loop."""

import json
import pytest
from pathlib import Path
from cardforge.document.model import CardForgeDocument, DocumentObject
from cardforge.document.loader import load_document, is_document_file, DocumentLoadError
from cardforge.document.adapter import (
    resolve_document_variables, adapt_to_legacy_config, _resolve_string
)
from cardforge.document.print_readme import generate_print_readme
from cardforge.manufacturing.report import ManufacturingReport
from cardforge.manufacturing.profiles import ManufacturingProfile


class TestDocumentModel:
    def test_from_dict_minimal(self):
        data = {
            "document": {"id": "test", "name": "Test"},
            "objects": [],
        }
        doc = CardForgeDocument.from_dict(data)
        assert doc.metadata.id == "test"
        assert doc.metadata.name == "Test"
        assert doc.objects == []

    def test_from_dict_full(self, tmp_path):
        data = {
            "document": {"id": "full", "name": "Full Doc", "version": "2.0"},
            "manufacturing": {"profile": "fdm-fine", "process": "fdm", "nozzle": 0.25, "layerHeight": 0.1, "material": "PETG"},
            "variables": {"name": "Javier"},
            "objects": [{
                "id": "card1", "type": "business-card",
                "width": 85, "height": 54, "thickness": 1.8,
                "theme": {"baseColor": "black"},
                "faces": {"front": {"features": []}},
            }],
            "exports": {"singleStl": True, "colorSeparatedStl": True},
        }
        doc = CardForgeDocument.from_dict(data)
        assert doc.metadata.version == "2.0"
        assert doc.manufacturing.nozzle == 0.25
        assert doc.variables["name"] == "Javier"
        assert len(doc.objects) == 1
        assert doc.objects[0].type == "business-card"
        assert doc.exports.single_stl is True
        assert doc.exports.color_separated_stl is True

    def test_to_dict_roundtrip(self):
        data = {
            "document": {"id": "rt", "name": "Roundtrip"},
            "objects": [{"id": "c1", "type": "business-card", "width": 85, "height": 54, "thickness": 1.8, "theme": {}, "faces": {}}],
        }
        doc = CardForgeDocument.from_dict(data)
        d = doc.to_dict()
        assert d["document"]["id"] == "rt"
        assert len(d["objects"]) == 1


class TestDocumentLoader:
    def test_loads_document(self, tmp_path):
        data = {"document": {"id": "test", "name": "Test"}, "objects": []}
        f = tmp_path / "test.cardforge.json"
        f.write_text(json.dumps(data))
        doc = load_document(str(f))
        assert doc.metadata.id == "test"

    def test_file_not_found(self):
        with pytest.raises(DocumentLoadError, match="not found"):
            load_document("/nonexistent/file.json")

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json")
        with pytest.raises(DocumentLoadError, match="Invalid JSON"):
            load_document(str(f))

    def test_is_document_detects(self, tmp_path):
        f = tmp_path / "doc.json"
        f.write_text(json.dumps({"document": {"id": "x"}, "objects": []}))
        assert is_document_file(str(f))

    def test_is_not_document(self, tmp_path):
        f = tmp_path / "legacy.json"
        f.write_text(json.dumps({"project": {"name": "Old"}}))
        assert not is_document_file(str(f))


class TestAdapter:
    def test_resolve_simple_variable(self):
        result = _resolve_string("Hello {{name}}", {"name": "Javier"}, {})
        assert result == "Hello Javier"

    def test_resolve_asset_variable(self):
        result = _resolve_string("Logo: {{assets.logo}}", {}, {"logo": "/path/logo.svg"})
        assert result == "Logo: /path/logo.svg"

    def test_resolve_unresolved_preserves(self):
        result = _resolve_string("{{unknown}}", {}, {})
        assert result == "{{unknown}}"

    def test_resolve_document_variables(self):
        doc = CardForgeDocument.from_dict({
            "document": {"id": "v", "name": "V"},
            "variables": {"name": "Javier", "title": "Dev"},
            "objects": [{
                "id": "c1", "type": "business-card",
                "width": 85, "height": 54, "thickness": 1.8,
                "theme": {},
                "faces": {"back": {"features": [
                    {"id": "t1", "type": "text-block", "lines": ["{{name}}", "{{title}}"]}
                ]}},
            }],
        })
        resolved = resolve_document_variables(doc)
        feat = resolved.objects[0].faces["back"]["features"][0]
        assert feat["lines"][0] == "Javier"
        assert feat["lines"][1] == "Dev"

    def test_adapt_to_legacy_config(self):
        doc = CardForgeDocument.from_dict({
            "document": {"id": "test", "name": "Test Card"},
            "variables": {"name": "Javier", "email": "j@test.com"},
            "objects": [{
                "id": "c1", "type": "business-card",
                "width": 85, "height": 54, "thickness": 1.8,
                "theme": {"baseColor": "black"},
                "faces": {"front": {"features": []}, "back": {"features": []}},
            }],
        })
        doc = resolve_document_variables(doc)
        config = adapt_to_legacy_config(doc)
        assert config["project"]["name"] == "test"
        assert config["object"]["width"] == 85
        assert config["owner"]["name"] == "Javier"

    def test_adapt_includes_qr_if_present(self):
        doc = CardForgeDocument.from_dict({
            "document": {"id": "t", "name": "T"},
            "variables": {"website": "https://example.com"},
            "objects": [{
                "id": "c1", "type": "business-card",
                "width": 85, "height": 54, "thickness": 1.8,
                "theme": {},
                "faces": {"back": {"features": [
                    {"id": "qr1", "type": "qr", "value": "{{website}}", "size": 24}
                ]}},
            }],
        })
        doc = resolve_document_variables(doc)
        config = adapt_to_legacy_config(doc)
        assert config["qr"]["enabled"] is True


class TestPrintReadme:
    def test_generates_file(self, tmp_path):
        report = ManufacturingReport(profile=ManufacturingProfile.fdm_standard())
        out = tmp_path / "README_PRINT.md"
        result = generate_print_readme("Test Card", report, [], out)
        assert result.exists()
        content = out.read_text()
        assert "Test Card" in content
        assert "Print-Ready" in content

    def test_includes_score(self, tmp_path):
        report = ManufacturingReport()
        out = tmp_path / "README_PRINT.md"
        generate_print_readme("Test", report, [], out)
        content = out.read_text()
        assert "100/100" in content

    def test_includes_stl_files(self, tmp_path):
        report = ManufacturingReport()
        stl1 = tmp_path / "card.stl"
        stl1.write_text("fake")
        out = tmp_path / "README_PRINT.md"
        generate_print_readme("Test", report, [stl1], out)
        content = out.read_text()
        assert "card.stl" in content

    def test_multi_color_instructions(self, tmp_path):
        report = ManufacturingReport()
        stl1 = tmp_path / "base.stl"
        stl2 = tmp_path / "text.stl"
        stl1.write_text("a")
        stl2.write_text("b")
        out = tmp_path / "README_PRINT.md"
        generate_print_readme("Test", report, [stl1, stl2], out)
        content = out.read_text()
        assert "Multi-Color" in content
