from __future__ import annotations

from typing import Protocol


class StepContext(dict):
    """Lightweight runtime container passed between workflow steps."""

    def copy(self) -> "StepContext":  # type: ignore[override]
        return StepContext(super().copy())


class BaseService(Protocol):
    """Protocol every workflow service should implement."""

    def setup(self) -> None: ...

    def execute(self, ctx: StepContext, params: dict) -> StepContext: ...

    def teardown(self) -> None: ...

