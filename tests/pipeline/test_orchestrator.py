"""Tests for pipeline orchestrator — chains stages and handles errors."""

import json
import pytest
from cardforge.pipeline.orchestrator import Pipeline, StageResult


class TestPipeline:
    """Test the pipeline orchestrator."""

    def test_runs_stages_in_order(self):
        """Stages should execute in the order they are registered."""
        order = []

        def stage_a(ctx):
            order.append("A")
            return StageResult.ok("A done")

        def stage_b(ctx):
            order.append("B")
            return StageResult.ok("B done")

        pipeline = Pipeline()
        pipeline.add_stage("load", stage_a)
        pipeline.add_stage("validate", stage_b)

        result = pipeline.run({})

        assert result.success
        assert order == ["A", "B"]

    def test_stops_on_first_error(self):
        """Pipeline should stop when a stage fails."""
        order = []

        def stage_a(ctx):
            order.append("A")
            return StageResult.ok("A done")

        def stage_b(ctx):
            order.append("B")
            return StageResult.error("B failed")

        def stage_c(ctx):
            order.append("C")
            return StageResult.ok("C done")

        pipeline = Pipeline()
        pipeline.add_stage("a", stage_a)
        pipeline.add_stage("b", stage_b)
        pipeline.add_stage("c", stage_c)

        result = pipeline.run({})

        assert not result.success
        assert order == ["A", "B"]  # C never runs
        assert "B failed" in result.error

    def test_passes_context_between_stages(self):
        """Each stage should receive and can modify the context."""

        def stage_a(ctx):
            ctx["loaded"] = True
            return StageResult.ok("loaded")

        def stage_b(ctx):
            assert ctx["loaded"] is True
            ctx["validated"] = True
            return StageResult.ok("validated")

        pipeline = Pipeline()
        pipeline.add_stage("load", stage_a)
        pipeline.add_stage("validate", stage_b)

        result = pipeline.run({})

        assert result.success
        assert result.context["loaded"] is True
        assert result.context["validated"] is True

    def test_records_stage_results(self):
        """Pipeline should record results from each executed stage."""

        def stage_a(ctx):
            return StageResult.ok("stage A ok")

        def stage_b(ctx):
            return StageResult.ok("stage B ok")

        pipeline = Pipeline()
        pipeline.add_stage("load", stage_a)
        pipeline.add_stage("validate", stage_b)

        result = pipeline.run({})

        assert "load" in result.stages
        assert result.stages["load"].status == "ok"
        assert result.stages["validate"].status == "ok"

    def test_integration_with_v2_stages(self, tmp_path):
        """Pipeline drives the real v2 load stage end to end."""
        import json

        from cardforge.pipeline.stages import load_document_stage

        doc = {
            "cardforge": "2.0",
            "meta": {"id": "t", "name": "T"},
            "object": {"outline": {"type": "rect", "width": 40, "height": 30},
                       "thickness": 1.5},
            "materials": [
                {"id": "base", "name": "Base", "color": "#111111", "role": "base"}],
            "variables": {"name": "Javier"},
            "faces": {"front": {"features": [{
                "id": "hi", "type": "text-block",
                "transform": {"x": 5, "y": 5}, "material": "base",
                "relief": {"mode": "emboss", "height": 0.4},
                "lines": ["Hello {{name}}"],
                "font": {"family": "Arial", "size": 4.0},
            }]}},
        }
        f = tmp_path / "t.cardforge.json"
        f.write_text(json.dumps(doc))

        pipeline = Pipeline()
        pipeline.add_stage("load", load_document_stage)
        result = pipeline.run({"document_path": str(f)})

        assert result.success
        loaded = result.context["document"]
        assert loaded.faces["front"].features[0].lines[0] == "Hello Javier"

    def test_integration_bad_document_fails_gracefully(self, tmp_path):
        """Pipeline with an invalid document fails with a clear error."""
        import json

        from cardforge.pipeline.stages import load_document_stage

        f = tmp_path / "bad.json"
        f.write_text(json.dumps({"project": {}}))

        pipeline = Pipeline()
        pipeline.add_stage("load", load_document_stage)
        result = pipeline.run({"document_path": str(f)})

        assert not result.success
        assert result.stages["load"].status == "error"
