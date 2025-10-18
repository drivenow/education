from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from logger import logger
from models.workflow import AssetConfig, StepConfig, WorkflowConfig
from orchestrator import Orchestrator
from progress_store import ProgressStore
from services.registry import ServiceRegistry


def load_workflow(path: Path | str) -> WorkflowConfig:
    path_obj = Path(path)
    raw = path_obj.read_text(encoding="utf-8")
    if hasattr(WorkflowConfig, "model_validate_json"):
        return WorkflowConfig.model_validate_json(raw)  # type: ignore[attr-defined]
    return WorkflowConfig.parse_raw(raw)


def run_workflow(
    workflow: WorkflowConfig,
    *,
    progress_path: Path | str | None = None,
    day: str | None = None,
    asset_id: str | None = None,
    no_playback: bool = False,
    registry: ServiceRegistry | None = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute the workflow against configured assets."""

    store_path = progress_path or Path(f"logs/{workflow.id}_progress.json")
    store = ProgressStore(store_path, workflow_id=workflow.id, assets=workflow.assets)

    service_registry = registry or ServiceRegistry()
    orchestrator = Orchestrator(workflow, service_registry)

    filtered_assets = _select_assets(workflow.assets, day=day, asset_id=asset_id)

    run_overrides: Dict[str, Dict[str, Any]] = {}
    if extra_context and "step_overrides" in extra_context:
        for step_id, params in extra_context["step_overrides"].items():
            run_overrides.setdefault(step_id, {}).update(params)

    if no_playback:
        for step in workflow.steps:
            if step.type in {"speak", "play", "playback"}:
                run_overrides.setdefault(step.id, {})["dry_run"] = True

    results: List[Dict[str, Any]] = []
    for asset in filtered_assets:
        if store.is_completed(asset.id):
            logger.info("Skipping completed asset %s", asset.id)
            continue

        store.attach_assets([asset])
        store.mark_started(asset)

        context_overrides = dict(extra_context or {})
        if run_overrides:
            overrides = dict(run_overrides)
            if "step_overrides" in context_overrides:
                merged = dict(context_overrides["step_overrides"])
                for key, value in overrides.items():
                    merged.setdefault(key, {}).update(value)
                overrides = merged
            context_overrides["step_overrides"] = overrides

        result = orchestrator.run_asset(asset, extra_context=context_overrides)
        results.append(result)

        artifacts = result.get("artifacts", {})
        playback = artifacts.get("playback", {})
        last_item = playback.get("last_played")
        if last_item:
            last_item = Path(last_item).name

        store.update_checkpoint(
            asset,
            last_item=last_item,
            progress_played=playback.get("segments_played"),
            progress_total=playback.get("segments_total"),
        )
        store.mark_completed(asset)
        store.flush()

    if not results:
        store.flush()
    return results


def _select_assets(
    assets: Iterable[AssetConfig],
    *,
    day: str | None = None,
    asset_id: str | None = None,
) -> List[AssetConfig]:
    selected: List[AssetConfig] = []
    day_normalized = day.lower() if day else None
    for asset in assets:
        if asset_id and asset.id != asset_id:
            continue
        if day_normalized and asset.crontab and asset.crontab.lower() != day_normalized:
            continue
        selected.append(asset)
    return selected


__all__ = ["load_workflow", "run_workflow"]

if __name__=="__main__":
    wf = load_workflow("config/workflows/history_science_english.json")
    run_workflow(
        wf,
        progress_path="config/workflows/history_science_english.json",  # 写回同一配置
        day="Mon",              # 只跑周一历史
        no_playback=False       # 如需跳过播放可改 True
    )
