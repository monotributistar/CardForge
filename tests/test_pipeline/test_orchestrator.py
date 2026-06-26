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

    def test_integration_with_real_config(self, tmp_path):
        """End-to-end: load + validate + resolve a config file."""
        config = {
            "project": {"name": "Test", "type": "business-card", "version": "0.1.0"},
            "manufacturing": {"process": "fdm", "nozzle": 0.4, "layerHeight": 0.2, "units": "mm"},
            "object": {"width": 85, "height": 54, "thickness": 1.8, "cornerRadius": 4},
            "owner": {"name": "Javier"},
            "faces": {
                "front": {
                    "features": [
                        {
                            "id": "t1",
                            "type": "text-block",
                            "fontSize": 3.0,
                            "lines": ["Hello {{owner.name}}"],
                        }
                    ]
                },
                "back": {"features": []},
            },
        }
        config_file = tmp_path / "test.json"
        config_file.write_text(json.dumps(config))

        from cardforge.config.loader import load_config
        from cardforge.config.validator import validate_config, ValidationError
        from cardforge.config.resolver import resolve_config

        def stage_load(ctx):
            ctx["raw"] = load_config(str(config_file))
            return StageResult.ok("config loaded")

        def stage_validate(ctx):
            try:
                ctx["validated"] = validate_config(ctx["raw"])
            except ValidationError as e:
                return StageResult.error(str(e))
            return StageResult.ok("config valid")

        def stage_resolve(ctx):
            ctx["resolved"] = resolve_config(ctx["validated"])
            return StageResult.ok("variables resolved")

        pipeline = Pipeline()
        pipeline.add_stage("load", stage_load)
        pipeline.add_stage("validate", stage_validate)
        pipeline.add_stage("resolve", stage_resolve)

        result = pipeline.run({})

        assert result.success
        resolved = result.context["resolved"]
        line = resolved["faces"]["front"]["features"][0]["lines"][0]
        assert line == "Hello Javier"

    def test_integration_bad_config_fails_gracefully(self, tmp_path):
        """Pipeline with invalid config should fail with a clear error."""
        bad_config = {"project": {}}  # missing required fields
        config_file = tmp_path / "bad.json"
        config_file.write_text(json.dumps(bad_config))

        from cardforge.config.loader import load_config
        from cardforge.config.validator import validate_config, ValidationError

        def stage_load(ctx):
            ctx["raw"] = load_config(str(config_file))
            return StageResult.ok("loaded")

        def stage_validate(ctx):
            try:
                validate_config(ctx["raw"])
            except ValidationError as e:
                return StageResult.error(str(e))
            return StageResult.ok("valid")

        pipeline = Pipeline()
        pipeline.add_stage("load", stage_load)
        pipeline.add_stage("validate", stage_validate)

        result = pipeline.run({})

        assert not result.success
        assert result.stages["load"].status == "ok"
        assert result.stages["validate"].status == "error"
