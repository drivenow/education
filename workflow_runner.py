from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import json

from models.workflow import AssetConfig, ServiceConfig, StepConfig, WorkflowConfig
from orchestrator import Orchestrator
from services.registry import ServiceRegistry


def build_workflow_config(
    audio_path: Path,
    repeats: int,
    translate: bool,
    model_size: str,
    device: str | None,
    initial_threshold: int,
    initial_repeats: int,
    label_with_stt: bool,
    enable_playback: bool,
) -> WorkflowConfig:
    services = [
        ServiceConfig(
            name="splitter",
            impl="services.defaults.create_splitter",
            options={
                "min_silence_len": 500,
                "silence_thresh": 16,
                "bitrate": "128k",
                "label_with_stt": label_with_stt,
                "model_size": model_size,
                "device": device or "cpu",
            },
        ),
        ServiceConfig(
            name="stt",
            impl="services.defaults.create_stt",
            options={
                "model_size": model_size,
                "device": device or "cpu",
            },
        ),
    ]

    steps = [
        StepConfig(id="split", type="split", service="splitter"),
        StepConfig(
            id="transcribe",
            type="transcribe",
            service="stt",
            params={"force_transcribe": False},
        ),
    ]

    if enable_playback:
        services.append(
            ServiceConfig(
                name="playback",
                impl="services.defaults.create_playback",
                options={
                    "initial_repeats": initial_repeats,
                    "initial_threshold": initial_threshold,
                },
            )
        )
        steps.append(
            StepConfig(
                id="play",
                type="speak",
                service="playback",
                params={
                    "repeats": repeats,
                    "translate": translate,
                    "skip_first": True,
                },
            )
        )

    assets = [AssetConfig(id=audio_path.stem, source_uri=str(audio_path))]

    return WorkflowConfig(
        id="cli_audio_listening",
        title="CLI Audio Listening Workflow",
        services=services,
        steps=steps,
        assets=assets,
    )


def load_workflow_config(path: Path) -> WorkflowConfig:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"无法解析配置文件：{path}") from exc

    if hasattr(WorkflowConfig, "model_validate_json"):
        return WorkflowConfig.model_validate_json(raw)  # type: ignore[attr-defined]
    if hasattr(WorkflowConfig, "model_validate"):
        return WorkflowConfig.model_validate(data)  # type: ignore[attr-defined]
    return WorkflowConfig.parse_obj(data)  # type: ignore[no-any-return]


def clone_workflow(cfg: WorkflowConfig) -> WorkflowConfig:
    if hasattr(cfg, "model_copy"):
        return cfg.model_copy(deep=True)  # type: ignore[attr-defined]
    return cfg.copy(deep=True)  # type: ignore[attr-defined]


def run_workflow(cfg: WorkflowConfig) -> None:
    registry = ServiceRegistry()
    orchestrator = Orchestrator(cfg, registry)

    for asset in cfg.assets:
        print(f"\n=== Asset: {asset.id} ({asset.source_uri}) ===")

        def on_progress(file_name: str, idx: int) -> None:
            print(f"[Progress][{asset.id}] #{idx}: {file_name}")

        ctx = orchestrator.run_asset(
            asset,
            extra_context={"callbacks": {"on_progress": on_progress}},
        )

        artifacts: dict[str, Any] = ctx.get("artifacts", {})
        transcripts = artifacts.get("transcripts", [])
        playback_info = artifacts.get("playback")

        if transcripts:
            print("[Transcripts]")
            for item in transcripts:
                print(f" - {Path(item['file']).name}: {item['text']}")

        if playback_info:
            print("[Playback]")
            for key, value in playback_info.items():
                print(f" {key}: {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用工作流框架执行音频切分、识别、播放流程（等同于 audio_process_and_replay 功能）。"
    )
    parser.add_argument("--config", type=Path, help="工作流配置文件（JSON）")
    parser.add_argument("--audio", type=Path, help="待处理的音频文件路径")
    parser.add_argument("--repeats", type=int, default=2, help="默认重复次数（>=初始阈值）")
    parser.add_argument(
        "--initial-repeats",
        type=int,
        default=1,
        help="前若干句子的重复次数",
    )
    parser.add_argument(
        "--initial-threshold",
        type=int,
        default=3,
        help="前多少个片段使用 initial-repeats",
    )
    parser.add_argument(
        "--model-size",
        type=str,
        default="small",
        help="Whisper 模型尺寸，如 tiny/base/small",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Whisper 推理设备，如 cpu/cuda。默认自动选择。",
    )
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="关闭中文翻译与提示朗读",
    )
    parser.add_argument(
        "--no-label-stt",
        action="store_true",
        help="切分阶段不执行 STT 重命名片段，减少耗时。",
    )
    parser.add_argument(
        "--no-playback",
        action="store_true",
        help="仅执行切分和识别，不播放音频（适合无音频设备环境）。",
    )
    parser.add_argument(
        "--asset-id",
        type=str,
        help="当使用 --config 时，仅运行指定的 asset id。",
    )
    parser.add_argument(
        "--day",
        type=str,
        help="当使用 --config 时，根据 metadata.day 过滤资产（如 Mon/Tue）。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.config:
        """
        这段逻辑的唯一作用，是让某个素材（asset）可以在 metadata.steps 里覆写同名步骤的参数或实现，从而实现像 weekly_listening.json 里那样：同样的工作流，周一的字母练习只重复 1 次且开启翻译，而歌曲步骤把 translate 关掉。
        如果把这一层去掉，所有素材都会严格使用全局 steps 上的默认配置，配置文件就没法表达“同一流程、不同教材小调”的需求了。
        """
        cfg = load_workflow_config(args.config)
        cfg = clone_workflow(cfg)

        if args.asset_id:
            cfg.assets = [asset for asset in cfg.assets if asset.id == args.asset_id]
        if args.day:
            cfg.assets = [
                asset
                for asset in cfg.assets
                if asset.metadata.get("day", "").lower() == args.day.lower()
            ]
        if not cfg.assets:
            raise ValueError("配置在筛选后没有可执行的资产。")

        if args.no_playback:
            for step in cfg.steps:
                if step.type == "speak":
                    step.enabled = False

        run_workflow(cfg)
        return

    if not args.audio:
        raise ValueError("未提供 --audio 或 --config，无法运行。")

    audio_path: Path = args.audio
    if not audio_path.exists():
        raise FileNotFoundError(f"未找到音频文件：{audio_path}")

    cfg = build_workflow_config(
        audio_path=audio_path,
        repeats=args.repeats,
        translate=not args.no_translate,
        model_size=args.model_size,
        device=args.device,
        initial_threshold=args.initial_threshold,
        initial_repeats=args.initial_repeats,
        label_with_stt=not args.no_label_stt,
        enable_playback=not args.no_playback,
    )

    run_workflow(cfg)


if __name__ == "__main__":
    main()
