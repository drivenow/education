from __future__ import annotations

import argparse
import json
import re
import os
from datetime import datetime
import hashlib
from pathlib import Path
from typing import Iterable, Optional

AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".flac", ".aac"}


def utc_now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def slugify(value: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", value.strip())
    slug = slug.strip("_") or "item"
    slug = slug.lower()
    if slug == "item":
        digest = hashlib.md5(value.encode("utf-8")).hexdigest()[:8]
        slug = f"item_{digest}"
    return slug


def normalize_path(path: Path) -> str:
    posix = path.as_posix()
    if posix.startswith("/mnt/") and len(posix) > 6:
        drive = posix[5].upper()
        rest = posix[6:]
        return f"{drive}:/{rest}"
    return posix


def collect_audio_files(directory: Path) -> list[Path]:
    # 使用递归遍历，确保子目录里的音频文件也能被发现
    return sorted(
        [
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in AUDIO_EXTS
        ]
    )


def default_steps_for_lang(lang: str) -> dict[str, dict]:
    lang_lower = lang.lower()
    if lang_lower.startswith("en"):
        return {
            "split": {"enabled": True, "label_with_stt": True},
            "play": {"translate": True, "skip_first": False, "repeats": 3},
        }
    return {
        "split": {"enabled": False, "label_with_stt": False},
        "play": {"translate": False, "skip_first": False, "repeats": 1},
    }


def build_asset(
    dir_slug: str,
    index: int,
    directory: Path,
    file_path: Path,
    lang: str,
    timestamp: str,
    mnt_convert: bool = False,
) -> dict:
    print(directory, file_path.name)
    return {
        "id": file_path.name,#f"{dir_slug}_{index:03d}_{slugify(file_path.stem)}",
        "source_uri": normalize_path(file_path.parent.resolve()) if mnt_convert else os.path.dirname(file_path.parent.resolve()),
        "file_name": file_path.name,
        "lang": lang,
        "is_valid": True,
        "completed": False,
        "status": None,
        "create_time": timestamp,
        "update_time": timestamp,
        "play_count": 0,
        "progress_played": 0,
        "progress_total": 0,
        "last_item": None,
        "steps": default_steps_for_lang(lang),
    }

def build_config(
    directory: Path,
    files: Iterable[Path],
    *,
    config_id: str,
    title: str,
    lang: str,
    max_session_seconds: Optional[int] = None,
    mnt_convert: bool = False,
) -> dict:
    timestamp = utc_now()
    dir_slug = slugify(directory.name)
    assets = [
        build_asset(dir_slug, idx, directory, file_path, lang, timestamp, mnt_convert)
        for idx, file_path in enumerate(files, start=1)
    ]
    
    services = [
        {
            "name": "splitter",
            "impl": "services.defaults.create_splitter",
            "options": {
                "min_silence_len": 500,
                "silence_thresh": 16
            },
        },
        {
            "name": "stt",
            "impl": "services.defaults.create_stt",
            "options": {
                "model_size": "small",
                "device": "cuda",
            },
        },
        {
            "name": "playback",
            "impl": "services.defaults.create_playback",
            "options": {
                "repeats": 1,
                "initial_repeats": 1,
                "initial_threshold": 3,
                "skip_first": True,
                "translate": lang.lower().startswith("en"),
            },
        },
    ]

    steps = [
        {"id": "split", "type": "split", "service": "splitter"},
        {"id": "transcribe", "type": "transcribe", "service": "stt"},
        {"id": "play", "type": "speak", "service": "playback"},
    ]

    config = {
        "id": config_id,
        "title": title,
        "services": services,
        "steps": steps,
        "assets": assets,
        "updated_at": timestamp,
    }
    if max_session_seconds is not None:
        config["max_session_seconds"] = max_session_seconds
    return config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate workflow config from an audio directory.")
    parser.add_argument("--directory", required=True, help="Directory containing audio files.")
    parser.add_argument("--lang", required=True, help="Language code, e.g. en or zh.")
    parser.add_argument("--output", required=True, help="Output config path (JSON).")
    parser.add_argument("--config-id", help="Config id, defaults to <dir>_<lang> slug.")
    parser.add_argument("--title", help="Config title.")
    parser.add_argument("--max-session-seconds", type=int, help="Optional max playback seconds per session.")
    parser.add_argument("--system_windows", type=int, default=1, help="Convert paths to windows-style if on mounted drive.")
    parser.add_argument("--sort", type=str, default="name_asc", choices=["time_asc", "time_desc", "name_asc"], help="Sort assets in ascending order.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    directory = Path(args.directory).expanduser()
    if directory.anchor and directory.drive:
        directory = Path(directory)
    if directory.as_posix().startswith("/mnt/"):
        directory = Path(directory.as_posix())
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    files = collect_audio_files(directory)
    if not files:
        raise ValueError(f"No audio files found in {directory}")

    config_id = args.config_id or f"{slugify(directory.name)}_{args.lang.lower()}"
    title = args.title or f"{directory.name} ({args.lang})"
    mnt_convert = True if args.system_windows else False
    sort = args.sort
    if sort == "time_asc":
        files = sorted(files, key=lambda x: x.stat().st_ctime)
    elif sort == "time_desc":
        files = sorted(files, key=lambda x: x.stat().st_ctime, reverse=True)
    elif sort == "name_asc":
        files = sorted(files, key=lambda x: x.name)

    config = build_config(
        directory=directory,
        files=files,
        config_id=config_id,
        title=title,
        lang=args.lang,
        max_session_seconds=args.max_session_seconds,
        mnt_convert=mnt_convert,
    )

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated config with {len(files)} assets at {output_path}")


if __name__ == "__main__":
    main()

"""
python scripts/generate_config.py \
  --directory "/mnt/x/BaiduNetdiskDownload/Fun for Starters 4th/176_4- Fun for Starters. 4th edition, Class Audio CD/Fun for Starters. 4th edition, 2017 Class Audio CD" \
  --lang en \
  --config-id fun_for_starters_audio \
  --title "Fun for Starters Audio" \
  --output config/mnt_fun_for_starters_audio.json \
  --max-session-seconds 60 \
  --system_windows 1


python scripts/generate_config.py \
  --directory "/mnt/x/BaiduNetdiskDownload/宫崎骏电影原生整理合集/第一辑" \
  --lang zh \
  --config-id gongqijun \
  --title gongqijun \
  --output config/gongqijun_audio.json \
  --max-session-seconds 300 \
  --system_windows 1
"""



