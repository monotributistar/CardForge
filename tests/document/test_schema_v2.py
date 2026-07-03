"""Tests for the v2 document schema — validation, round-trip, referential rules."""

import pytest

from cardforge.document.schema_v2 import (
    DocumentV2, DocumentValidationError, validate_v2, is_v2,
)


def minimal_doc(**overrides):
    doc = {
        "cardforge": "2.0",
        "meta": {"id": "test-card", "name": "Test Card"},
        "object": {
            "outline": {"type": "rounded-rect", "width": 85, "height": 54, "radius": 4},
            "thickness": 1.8,
        },
        "materials": [
            {"id": "base", "name": "Base", "color": "#1a1a1a", "slot": 1, "role": "base"},
            {"id": "text", "name": "Text", "color": "#ffffff", "slot": 2, "role": "text"},
        ],
        "faces": {"front": {"features": []}, "back": {"features": []}},
    }
    doc.update(overrides)
    return doc


def text_feature(**overrides):
    feat = {
        "id": "t1",
        "type": "text-block",
        "transform": {"x": 10, "y": 12},
        "material": "text",
        "relief": {"mode": "emboss", "height": 0.4},
        "lines": ["Hello"],
        "font": {"family": "Montserrat", "size": 3.5},
    }
    feat.update(overrides)
    return feat


class TestValidation:
    def test_minimal_valid(self):
        validate_v2(minimal_doc())  # no raise

    def test_is_v2(self):
        assert is_v2(minimal_doc())
        assert not is_v2({"document": {}, "objects": []})

    def test_missing_materials_rejected(self):
        doc = minimal_doc()
        doc["materials"] = []
        with pytest.raises(DocumentValidationError):
            validate_v2(doc)

    def test_bad_color_rejected(self):
        doc = minimal_doc()
        doc["materials"][0]["color"] = "black"
        with pytest.raises(DocumentValidationError, match="color"):
            validate_v2(doc)

    def test_unknown_material_reference_rejected(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [text_feature(material="gold")]
        with pytest.raises(DocumentValidationError, match="unknown material 'gold'"):
            validate_v2(doc)

    def test_duplicate_feature_ids_rejected(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [text_feature(), text_feature()]
        with pytest.raises(DocumentValidationError, match="duplicate"):
            validate_v2(doc)

    def test_emboss_requires_height(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [
            text_feature(relief={"mode": "emboss"})]
        with pytest.raises(DocumentValidationError):
            validate_v2(doc)

    def test_deboss_backed_requires_floor(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [
            text_feature(relief={"mode": "deboss-backed", "depth": 0.6})]
        with pytest.raises(DocumentValidationError):
            validate_v2(doc)

    def test_deboss_backed_floor_material_must_exist(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [text_feature(relief={
            "mode": "deboss-backed", "depth": 0.6,
            "floorMaterial": "gold", "floorThickness": 0.2})]
        with pytest.raises(DocumentValidationError, match="unknown floorMaterial"):
            validate_v2(doc)

    def test_deboss_backed_floor_must_differ_from_feature_material(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [text_feature(relief={
            "mode": "deboss-backed", "depth": 0.6,
            "floorMaterial": "text", "floorThickness": 0.2})]
        with pytest.raises(DocumentValidationError, match="must differ"):
            validate_v2(doc)

    def test_cut_relief_valid_without_dims(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [text_feature(relief={"mode": "cut"})]
        validate_v2(doc)

    def test_icon_color_map_references_materials(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [{
            "id": "i1", "type": "icon",
            "transform": {"x": 5, "y": 5}, "material": "text",
            "relief": {"mode": "emboss", "height": 0.3},
            "width": 12, "svgAsset": "logo",
            "colorMap": {"#ff0000": "nonexistent"},
        }]
        with pytest.raises(DocumentValidationError, match="colorMap"):
            validate_v2(doc)

    def test_path_outline(self):
        doc = minimal_doc()
        doc["object"]["outline"] = {
            "type": "path", "svgPath": "M0,0 L85,0 L85,54 L0,54 Z",
            "width": 85, "height": 54}
        validate_v2(doc)

    def test_variable_font_axes(self):
        doc = minimal_doc()
        doc["faces"]["front"]["features"] = [text_feature(
            font={"family": "Inter", "size": 4.0, "axes": {"wght": 650, "wdth": 90}})]
        validate_v2(doc)


class TestRoundTrip:
    def test_from_dict_to_dict_stable(self):
        doc = minimal_doc()
        doc["variables"] = {"name": "Javier"}
        doc["faces"]["front"]["features"] = [
            text_feature(),
            {
                "id": "q1", "type": "qr", "transform": {"x": 55, "y": 15},
                "material": "text", "relief": {"mode": "emboss", "height": 0.4},
                "qrType": "url", "fields": {"url": "https://x.dev"}, "size": 24,
            },
            {
                "id": "s1", "type": "shape", "shapeType": "frame",
                "transform": {"x": 0, "y": 0}, "material": "text",
                "relief": {"mode": "deboss", "depth": 0.2},
                "strokeWidth": 1.0, "inset": 2.0,
            },
        ]
        model = DocumentV2.from_dict(doc)
        out = model.to_dict()
        # Round-trip must re-validate and preserve every feature
        model2 = DocumentV2.from_dict(out)
        assert model2.to_dict() == out
        assert [f.id for f in model2.faces["front"].features] == ["t1", "q1", "s1"]

    def test_typed_access(self):
        model = DocumentV2.from_dict(minimal_doc(
            faces={"front": {"features": [text_feature()]}}))
        feat = model.faces["front"].features[0]
        assert feat.font.family == "Montserrat"
        assert feat.relief.mode == "emboss"
        assert feat.relief.height == 0.4
        assert model.base_material.id == "base"
        assert model.material_by_id("text").color == "#ffffff"

    def test_deboss_backed_round_trip(self):
        doc = minimal_doc()
        doc["materials"].append(
            {"id": "accent", "name": "Gold", "color": "#d4af37", "slot": 3})
        doc["faces"]["front"]["features"] = [text_feature(relief={
            "mode": "deboss-backed", "depth": 0.6,
            "floorMaterial": "accent", "floorThickness": 0.2})]
        model = DocumentV2.from_dict(doc)
        r = model.faces["front"].features[0].relief
        assert (r.mode, r.depth, r.floor_material, r.floor_thickness) == \
            ("deboss-backed", 0.6, "accent", 0.2)
        assert model.to_dict()["faces"]["front"]["features"][0]["relief"] == {
            "mode": "deboss-backed", "depth": 0.6,
            "floorMaterial": "accent", "floorThickness": 0.2}
