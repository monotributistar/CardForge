"""Pipeline orchestrator — chains stages with error handling.

The Pipeline is a linear stage runner. Stages are registered in order
and executed sequentially. Each stage receives a shared context dict.
If any stage returns an error, the pipeline stops and reports failure.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict


# ── Stage result ──────────────────────────────────────────────────────────────

@dataclass
class StageResult:
    """Result from a single pipeline stage."""

    status: str  # "ok" or "error"
    message: str

    @classmethod
    def ok(cls, message: str = "") -> "StageResult":
        """Create a successful stage result."""
        return cls(status="ok", message=message)

    @classmethod
    def error(cls, message: str) -> "StageResult":
        """Create a failed stage result."""
        return cls(status="error", message=message)


# ── Pipeline result ───────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """Result from a full pipeline run."""

    success: bool
    context: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    stages: Dict[str, StageResult] = field(default_factory=dict)


# ── Pipeline ──────────────────────────────────────────────────────────────────

# A stage function receives a mutable context dict and returns a StageResult.
StageFn = Callable[[Dict[str, Any]], StageResult]


class Pipeline:
    """Linear pipeline that chains stage functions.

    Usage:
        pipeline = Pipeline()
        pipeline.add_stage("load", load_stage)
        pipeline.add_stage("validate", validate_stage)
        result = pipeline.run(initial_context={})
        if result.success:
            print("Pipeline complete")
    """

    def __init__(self) -> None:
        self._stages: list[tuple[str, StageFn]] = []

    def add_stage(self, name: str, fn: StageFn) -> None:
        """Register a stage function.

        Args:
            name: Unique stage name (used for reporting).
            fn: Callable that takes a context dict and returns StageResult.
        """
        self._stages.append((name, fn))

    def run(self, context: Dict[str, Any]) -> PipelineResult:
        """Execute all registered stages in order.

        Stops on the first stage that returns an error.

        Args:
            context: Initial context dict passed to the first stage.

        Returns:
            PipelineResult with success status, final context, and per-stage results.
        """
        result = PipelineResult(success=True, context=context)

        for name, fn in self._stages:
            stage_result = fn(context)
            result.stages[name] = stage_result

            if stage_result.status == "error":
                result.success = False
                result.error = f"Stage '{name}' failed: {stage_result.message}"
                break

        return result
