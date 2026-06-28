"""Tests for prototype documents — load, validate, and check constraints."""

import json
import pytest
from pathlib import Path
from cardforge.document.loader import load_document
from cardforge.document.adapter import resolve_document_variables, adapt_to_legacy_config


PROTOTYPES_DIR = Path(__file__).resolve().parent.parent.parent / "examples" / "prototypes"
PROTOTYPE_FILES = [
    "card_minimal.cardforge.json",
    "card_dark_luxury.cardforge.json",
    "card_tech_pattern.cardforge.json",
]


def _load_prototype(filename: str):
    path = PROTOTYPES_DIR / filename
    doc = load_document(str(path))
    doc = resolve_document_variables(doc)
    return doc


class TestPrototypeDocuments:
    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_loads_without_error(self, filename):
        """All prototypes should load successfully."""
        doc = load_document(str(PROTOTYPES_DIR / filename))
        assert doc.metadata.id != ""
        assert doc.metadata.name != ""

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_has_manufacturing_profile(self, filename):
        """All prototypes must specify a manufacturing profile."""
        doc = _load_prototype(filename)
        assert doc.manufacturing.profile in ("fdm-standard", "fdm-fine", "sla")
        assert doc.manufacturing.nozzle > 0

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_has_at_least_one_object(self, filename):
        doc = _load_prototype(filename)
        assert len(doc.objects) >= 1
        obj = doc.objects[0]
        assert obj.type == "business-card"
        assert obj.width == 85.0
        assert obj.height == 54.0

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_adapts_to_legacy_config(self, filename):
        """All prototypes must adapt to legacy config format."""
        doc = _load_prototype(filename)
        config = adapt_to_legacy_config(doc)
        assert "project" in config
        assert "object" in config
        assert "faces" in config

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_has_front_and_back_faces(self, filename):
        doc = _load_prototype(filename)
        obj = doc.objects[0]
        assert "front" in obj.faces
        assert "back" in obj.faces

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_has_qr_on_back(self, filename):
        """Every prototype should have a QR code somewhere."""
        doc = _load_prototype(filename)
        obj = doc.objects[0]
        found_qr = False
        for face_id in ("front", "back"):
            for feat in obj.faces.get(face_id, {}).get("features", []):
                if feat.get("type") == "qr":
                    found_qr = True
                    size = feat.get("size", 0)
                    if isinstance(size, dict):
                        size = size.get("width", 0)
                    assert size >= 24, f"QR too small in {filename}: {size}mm"
        assert found_qr, f"No QR found in {filename}"

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_has_exports_enabled(self, filename):
        doc = _load_prototype(filename)
        assert doc.exports.single_stl is True
        assert doc.exports.color_separated_stl is True

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_has_text_features(self, filename):
        """Every prototype should have at least one text feature."""
        doc = _load_prototype(filename)
        obj = doc.objects[0]
        found_text = False
        for face_id in ("front", "back"):
            for feat in obj.faces.get(face_id, {}).get("features", []):
                if feat.get("type") == "text-block":
                    found_text = True
                    # Check minimum font size
                    fs = feat.get("fontSize", 0)
                    assert fs >= 3.0, f"Font too small in {filename}: {fs}mm"
        assert found_text, f"No text found in {filename}"

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_has_valid_thickness(self, filename):
        doc = _load_prototype(filename)
        obj = doc.objects[0]
        assert 1.0 <= obj.thickness <= 2.2, f"Bad thickness: {obj.thickness}"

    @pytest.mark.parametrize("filename", PROTOTYPE_FILES)
    def test_has_corner_radius(self, filename):
        doc = _load_prototype(filename)
        obj = doc.objects[0]
        assert obj.corner_radius >= 2.0, f"Corner radius too small: {obj.corner_radius}"
