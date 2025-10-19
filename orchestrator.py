from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, Optional
import time
from models.workflow import AssetConfig, StepConfig, WorkflowConfig
from services.base import StepContext
from services.registry import ServiceRegistry


class Orchestrator:
    """Execute workflow steps for each asset using the declared services."""

    def __init__(self, workflow: WorkflowConfig, registry: Optional[ServiceRegistry] = None) -> None:
        self.workflow = workflow
        self.session_limit = workflow.max_session_seconds or 30*60
        self.registry = registry or ServiceRegistry()
        self._services: Dict[str, Any] = {}

    def run_all(
        self,
        assets: Optional[Iterable[AssetConfig]] = None,
        *,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        t1 = time.time()
        iterable = assets or self.workflow.assets
        for asset in iterable:
            t2 = time.time()
            if t2 - t1 > self.session_limit*0.95:
                raise TimeoutError(f"Asset {asset.id} stop after {t2 - t1} seconds")
            yield self.run_asset(asset, extra_context=extra_context)

    def run_asset(
        self,
        asset: AssetConfig,
        *,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        artifacts: Dict[str, Any] = {}
        step_results: list[Dict[str, Any]] = []
        extras = dict[str, Any](extra_context or {})
        for step in self.workflow.steps:
            result = self._run_step(step, asset, artifacts, extras)
            step_results.append({"id": step.id, "result": result})
        return {"asset": asset, "artifacts": artifacts}

    # --------------------------------------------------------------------- utils
    def _run_step(
        self,
        step: StepConfig,
        asset: AssetConfig,
        artifacts: Dict[str, Any],
        extras: Dict[str, Any],
    ) -> Any:
        service = self._get_service(step.service)
        asset_overrides = asset.step_overrides(step.id)
        run_overrides = {}
        if extras:
            run_overrides = extras.get("step_overrides", {}).get(step.id, {})
        combined_overrides = dict(asset_overrides)
        combined_overrides.update(run_overrides)
        settings = step.merged_params(combined_overrides)
        if "max_session_seconds" not in settings or settings.get("max_session_seconds") is None:
            workflow_limit = getattr(self.workflow, "max_session_seconds", 30*60)
            settings["max_session_seconds"] = workflow_limit
        context = StepContext(
            workflow=self.workflow,
            asset=asset,
            step=step,
            settings=settings,
            artifacts=artifacts,
            extras=extras,
        )
        return service.run(context)

    def _get_service(self, name: str) -> Any:
        if name not in self._services:
            service_config = self.workflow.service_map().get(name)
            if not service_config:
                raise KeyError(f"Service '{name}' not found in workflow configuration.")
            self._services[name] = self.registry.get(service_config)
        return self._services[name]
