"""Tests for material SCAD generator and STL parts exporter."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cardforge.scad.material_groups import group_features_by_material, get_material_filename
from cardforge.scad.material_generator import generate_material_scad_files
from cardforge.export.stl_parts import export_material_stls, OpenSCADJob, run_openscad_many, OpenSCADNotFoundError
from cardforge.export.openscad_cli import OpenSCADResult
from cardforge.assets.asset_manager import GeneratedAssets
from cardforge.export.paths import prepare_export_paths
from cardforge.domain.card import Card
from cardforge.domain.face import Face
from cardforge.domain.layer import Layer
from cardforge.domain.feature import TextBlockFeature, QRCodeFeature, PatternFeature
from cardforge.domain.geometry import Position, Size
from cardforge.domain.relief import Relief
from cardforge.domain.material import Material, DEFAULT_MATERIALS


def _make_card(features_front=None, features_back=None):
    front = Face(id="front", width=85, height=54)
    back = Face(id="back", width=85, height=54)
    if features_front:
        front.layers = [Layer(id="content", features=features_front)]
    if features_back:
        back.layers = [Layer(id="content", features=features_back)]
    return Card(
        id="test", name="Test", width=85, height=54, thickness=1.8,
        corner_radius=4, materials=DEFAULT_MATERIALS,
        faces={"front": front, "back": back},
    )


class TestMaterialFilename:
    def test_base_format(self):
        name = get_material_filename("base", "Black", 1)
        assert name.startswith("01_base_")
        assert name.endswith(".stl")

    def test_deterministic(self):
        a = get_material_filename("text", "White", 2)
        b = get_material_filename("text", "White", 2)
        assert a == b

    def test_different_indices(self):
        a = get_material_filename("base", "black", 1)
        b = get_material_filename("text", "white", 2)
        assert a != b
        assert a.startswith("01")
        assert b.startswith("02")

    def test_special_chars_sanitized(self):
        name = get_material_filename("neon-pink", "Hot Pink!", 3)
        assert "!" not in name
        assert " " not in name


class TestMaterialScadGenerator:
    def test_generates_scad_for_each_material(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        text = TextBlockFeature(
            id="t1", lines=["A"], material=DEFAULT_MATERIALS["text"],
            position=Position(10, 10), size=Size(20, 10),
        )
        accent = TextBlockFeature(
            id="t2", lines=["B"], material=DEFAULT_MATERIALS["accent"],
            position=Position(10, 20), size=Size(20, 10),
        )
        card = _make_card(features_front=[text, accent])
        groups = group_features_by_material(card)
        paths = generate_material_scad_files(card, groups, GeneratedAssets(), export)
        assert "base" in paths
        assert "text" in paths
        assert "accent" in paths

    def test_base_scad_contains_card_base(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        card = _make_card()
        groups = group_features_by_material(card)
        paths = generate_material_scad_files(card, groups, GeneratedAssets(), export)
        base_scad = paths["base"].read_text()
        assert "card_base(" in base_scad

    def test_text_scad_does_not_contain_card_base(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        text = TextBlockFeature(
            id="t1", lines=["A"], material=DEFAULT_MATERIALS["text"],
            position=Position(10, 10), size=Size(20, 10),
        )
        card = _make_card(features_front=[text])
        groups = group_features_by_material(card)
        paths = generate_material_scad_files(card, groups, GeneratedAssets(), export)
        text_scad = paths["text"].read_text()
        assert "card_base(" not in text_scad

    def test_qr_scad_contains_svg_import(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        qr = QRCodeFeature(
            id="qr1", material=DEFAULT_MATERIALS["text"],
            position=Position(50, 15), size=Size(24, 24),
        )
        card = _make_card(features_back=[qr])
        # Create fake QR asset
        qr_path = export.assets_dir / "qr_qr1.svg"
        qr_path.parent.mkdir(parents=True, exist_ok=True)
        qr_path.write_text("<svg></svg>")
        assets = GeneratedAssets(qr_paths=[qr_path])
        groups = group_features_by_material(card)
        paths = generate_material_scad_files(card, groups, assets, export)
        text_scad = paths["text"].read_text()
        assert "svg_emboss_layer" in text_scad

    def test_scads_in_parts_subdir(self, tmp_path):
        export = prepare_export_paths("Test", base_dir=tmp_path)
        card = _make_card()
        groups = group_features_by_material(card)
        paths = generate_material_scad_files(card, groups, GeneratedAssets(), export)
        for p in paths.values():
            assert "parts" in str(p)


class TestRunOpenscadMany:
    def test_runs_all_jobs(self, tmp_path):
        jobs = [
            OpenSCADJob(scad_path=tmp_path / "a.scad", stl_path=tmp_path / "a.stl", material_id="base"),
            OpenSCADJob(scad_path=tmp_path / "b.scad", stl_path=tmp_path / "b.stl", material_id="text"),
        ]
        for j in jobs:
            j.scad_path.write_text("")
            j.stl_path.write_text("fake")

        with patch("cardforge.export.stl_parts.run_openscad") as mock_run:
            def side_effect(scad, stl, **kw):
                return OpenSCADResult(success=True, returncode=0, stdout="", stderr="", output_file=stl)
            mock_run.side_effect = side_effect
            results = run_openscad_many(jobs)
            assert len(results) == 2
            assert all(r.success for r in results)

    def test_handles_not_found_gracefully(self, tmp_path):
        jobs = [OpenSCADJob(scad_path=tmp_path / "a.scad", stl_path=tmp_path / "a.stl", material_id="base")]
        jobs[0].scad_path.write_text("")

        with patch("cardforge.export.stl_parts.run_openscad", side_effect=OpenSCADNotFoundError("nope")):
            results = run_openscad_many(jobs)
            assert len(results) == 1
            assert not results[0].success
