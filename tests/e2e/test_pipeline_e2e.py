"""End-to-end: document file → pipeline → 3MF/STL files on disk."""

import json
import zipfile
from pathlib import Path

import pytest

from cardforge.pipeline.stages import build_pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES = sorted((PROJECT_ROOT / "examples").rglob("*.cardforge.json"))


class TestPipelineE2E:
    @pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.name)
    def test_full_build(self, example, tmp_path):
        pipeline = build_pipeline(export_stl=True)
        result = pipeline.run({
            "document_path": str(example),
            "exports_dir": str(tmp_path),
            "asset_root": str(PROJECT_ROOT),
            # examples are v1-authored; back-face emboss warnings are expected,
            # errors are not — but don't block on legacy authoring choices
            "ignore_manufacturing_errors": True,
            "ignore_constraint_errors": True,
        })
        assert result.success, result.error

        doc = result.context["document"]
        out = tmp_path / doc.meta.id
        threemf = out / f"{doc.meta.id}.3mf"
        assert threemf.exists() and threemf.stat().st_size > 1000
        with zipfile.ZipFile(threemf) as zf:
            assert "3D/3dmodel.model" in zf.namelist()
        stls = list((out / "stl").glob("*.stl"))
        assert stls, "per-material STLs must be written"
        assert (out / "reports" / "manufacturing.json").exists()

    def test_error_document_fails_cleanly(self, tmp_path):
        bad = tmp_path / "bad.cardforge.json"
        bad.write_text(json.dumps({"not": "a document"}))
        result = build_pipeline().run({
            "document_path": str(bad), "exports_dir": str(tmp_path)})
        assert not result.success
        assert "Not a CardForge document" in result.error
