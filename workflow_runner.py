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
    if not filtered_assets:
        store.flush()
        return []
    # 循环播放逻辑要在真正播放前就能读到每个素材对应的 TaskMeta
    # 记录当前所有素材的播放次数，便于循环模式下保持均衡
    store.attach_assets(filtered_assets)
    play_counts: List[int] = []
    for asset in filtered_assets:
        record = store.get_record(asset.id)
        if record is not None:
            play_counts.append(int(record.play_count or 0))
        else:
            play_counts.append(int(getattr(asset, "play_count", 0) or 0))
    # 当前的最小播放次数
    min_play_count = min(play_counts) if play_counts else 0

    flag_loop_assets = bool(getattr(workflow, "flag_loop_assets", False)) #是否启用循环播放
    flag_stop_due_to_time = False # 播放时间是否已经超时
    flag_cycle_played = False # 是否播放过任何素材
    results: List[Dict[str, Any]] = []
    t1 = time.time()
    session_limit = workflow.max_session_seconds or 30 * 60

    while True:
        for asset in filtered_assets:
            if not flag_loop_assets:
                if store.is_completed(asset.id):
                    logger.info("Skipping completed asset %s", asset.id)
                    continue
            else:
                # 仅当该文件与最小播放次数持平或存在未完成进度时才进入本轮
                record = store.get_record(asset.id)
                record_play_count = int(
                    (record.play_count if record is not None else getattr(asset, "play_count", 0)) or 0
                )
                has_partial_progress = bool(
                    record
                    and record.progress_total
                    and record.progress_played < record.progress_total
                )
                if not has_partial_progress and record_play_count > min_play_count:
                    continue

            t2 = time.time()
            if t2 - t1 > session_limit * 0.95:
                logger.info("Session limit %s seconds reached, stopping", session_limit)
                flag_stop_due_to_time = True
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
            flag_cycle_played = True

        if flag_stop_due_to_time or not flag_loop_assets:
            break
        if not flag_cycle_played:
            # 未播放任何素材，说明进度已同步，结束循环
            break

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
    flag = "gongqijun"
    if flag == "fun_for_starters":
        wf = load_workflow("config/fun_for_starters_audio.json")
        run_workflow(
            wf,
            progress_path="config/fun_for_starters_audio.json",  # 写回同一配置
        )
    elif flag == "gongqijun":
        wf = load_workflow("config/gongqijun_audio.json")
        run_workflow(
            wf,
            progress_path="config/gongqijun_audio.json",  # 写回同一配置
        )
    else:
        raise Exception()

