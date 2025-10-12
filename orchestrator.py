from __future__ import annotations

from collections import defaultdict
from typing import Iterator

from models.workflow import AssetConfig, WorkflowConfig
from services.base import StepContext
from services.registry import ServiceRegistry


class Orchestrator:
    """Runs workflow steps for each configured asset."""

    def __init__(self, config: WorkflowConfig, registry: ServiceRegistry):
        self._config = config
        self._registry = registry
        self._services = {
            svc.name: registry.create(svc.impl, svc.options or {}) for svc in config.services
        }

    def run_asset(
        self, asset: AssetConfig, extra_context: dict | None = None
    ) -> StepContext:
        ctx = StepContext(asset=asset, artifacts=defaultdict(dict))
        if extra_context:
            ctx.update(extra_context)

        asset_metadata = getattr(asset, "metadata", {}) or {}
        step_overrides = asset_metadata.get("steps", {})

        for step in self._config.steps:
            if not step.enabled:
                continue
            service = self._services.get(step.service)
            if service is None:
                raise KeyError(f"Service {step.service} not registered.")

            effective_params = dict(step.params)
            # 如果某个播放文件定义了新的步骤，允许替换原来的步骤实现，但是不能增加或减少步骤
            if step_overrides:
                override = step_overrides.get(step.id)
                if override:
                    effective_params.update(override)
            ctx = service.execute(ctx, effective_params)
        return ctx

    def run_all(self) -> Iterator[StepContext]:
        for asset in self._config.assets:
            yield self.run_asset(asset)
