from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import time
from logger import logger
from models.workflow import AssetConfig, WorkflowConfig
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
    asset_id: str | None = None,
    registry: ServiceRegistry | None = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute the workflow against configured assets."""

    store_path = progress_path or Path(f"logs/{workflow.id}_progress.json")
    store = ProgressStore(store_path, workflow_id=workflow.id, assets=workflow.assets)

    service_registry = registry or ServiceRegistry()
    orchestrator = Orchestrator(workflow, service_registry)

    filtered_assets = _select_assets(workflow.assets, asset_id=asset_id)

    results: List[Dict[str, Any]] = []
    t1 = time.time()
    session_limit = workflow.max_session_seconds or 30*60
    for asset in filtered_assets:
        if store.is_completed(asset.id):
            logger.info("Skipping completed asset %s", asset.id)
            continue
        t2 = time.time()
        if t2 - t1 > session_limit*0.95:
            logger.info("Session limit %s seconds reached, stopping", session_limit)
            break
        store.attach_assets([asset])
        store.mark_started(asset)

        context_overrides = dict(extra_context or {})

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
    asset_id: str | None = None,
) -> List[AssetConfig]:
    selected: List[AssetConfig] = []
    for asset in assets:
        if asset_id and asset.id != asset_id:
            continue
        selected.append(asset)
    return selected


__all__ = ["load_workflow", "run_workflow"]

if __name__=="__main__":
    wf = load_workflow("config/workflows/mnt_fun_for_starters_audio.json")
    run_workflow(
        wf,
        progress_path="config/workflows/fun_for_starters_audio.json",  # 写回同一配置
    )
