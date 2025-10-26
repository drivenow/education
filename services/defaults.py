from __future__ import annotations

import re
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from logger import logger
from services.base import BaseService, ServiceError, StepContext
import soundfile as sf

try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
except:
    raise ServiceError("pydub is required for audio splitting.")

# Optional STT/translation/TTS backends
from speech2text_model import speech_to_text
from translate_model import traslate_text
from speaker_model import speak_text
from audio_utils import play_audio, resample_audio


def create_splitter(**options: Any) -> "SplitterService":
    return SplitterService(**options)


def create_stt(**options: Any) -> "STTService":
    return STTService(**options)


def create_playback(**options: Any) -> "PlaybackService":
    return PlaybackService(**options)


@dataclass
class SplitterService(BaseService):
    min_silence_len: int = 700
    silence_thresh: int = 16
    keep_silence: int = 200
    sample_rate: int = 16000
    normalize: bool = True
    enabled: bool = True
    force_rebuild: bool = False

    def run(self, context: StepContext) -> Dict[str, Any]:
        params = self._merge_params(context.settings)
        if not params.get("enabled", True):
            result = {"skipped": True}
            context.artifacts["split"] = result
            return result
            
        source_path = context.asset.resolved_path()
        if not source_path.exists():
            raise ServiceError(f"Audio source not found: {source_path}")

        target_dir = self._resolve_target_dir(source_path, params)
        target_dir.mkdir(parents=True, exist_ok=True)

        reuse_existing = (
            not params.get("force_rebuild", self.force_rebuild)
            and any(target_dir.glob("chunk*.wav"))
        )
        if reuse_existing:
            chunk_paths = sorted(str(path) for path in target_dir.glob("chunk*.wav"))
            transcripts = context.artifacts.get("transcripts", [])
            result = {
                "target_dir": str(target_dir),
                "chunks": chunk_paths,
                "transcripts": transcripts,
                "reused": True,
            }
            context.artifacts.update(
                {"split": result, "chunks": chunk_paths, "transcripts": transcripts}
            )
            return result

        audio = self._load_audio(source_path)
        silence_threshold = audio.dBFS - int(params.get("silence_thresh", self.silence_thresh))
        min_silence = int(params.get("min_silence_len", self.min_silence_len))
        keep_silence = int(params.get("keep_silence", self.keep_silence))

        logger.info(
            "Splitting audio '%s' -> %s (min_silence=%sms, silence_thresh=%sdB, keep=%sms)",
            source_path,
            target_dir,
            min_silence,
            silence_threshold,
            keep_silence,
        )

        segments = split_on_silence(
            audio,
            min_silence_len=min_silence,
            silence_thresh=silence_threshold,
            keep_silence=keep_silence,
        )

        if not segments:
            segments = [audio]

        chunk_paths: List[str] = []
        for idx, segment in enumerate(segments):
            chunk = self._prepare_segment(segment, params)
            chunk_path = target_dir / f"chunk{idx:04d}.wav"
            chunk.export(chunk_path, format="wav")
            if params.get("sample_rate"):
                try:
                    resample_audio(str(chunk_path), sr=int(params["sample_rate"]))
                except Exception as exc:  # pragma: no cover
                    logger.warning("Failed to resample chunk %s: %s", chunk_path, exc)
            chunk_paths.append(str(chunk_path))

        result = {
            "target_dir": str(target_dir),
            "chunks": chunk_paths,
            "reused": False,
        }
        context.artifacts.update({"split": result, "chunks": chunk_paths})
        return result

    def _merge_params(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        params = {
            "min_silence_len": self.min_silence_len,
            "silence_thresh": self.silence_thresh,
            "keep_silence": self.keep_silence,
            "sample_rate": self.sample_rate,
            "normalize": self.normalize,
            "enabled": self.enabled,
            "force_rebuild": self.force_rebuild,
        }
        params.update({k: v for k, v in overrides.items() if v is not None})
        return params

    def _resolve_target_dir(self, source_path: Path, params: Dict[str, Any]) -> Path:
        if params.get("target_dir"):
            return Path(params["target_dir"])
        return source_path.parent / f"{source_path.stem}_chunks"

    def _load_audio(self, source_path: Path) -> AudioSegment:
        suffix = source_path.suffix.lower()
        if suffix == ".mp3":
            return AudioSegment.from_mp3(source_path)
        if suffix == ".wav":
            return AudioSegment.from_wav(source_path)
        if suffix == ".m4a":
            return AudioSegment.from_file(source_path, "m4a")
        return AudioSegment.from_file(source_path)

    def _prepare_segment(self, segment: AudioSegment, params: Dict[str, Any]) -> AudioSegment:
        if params.get("normalize", True):
            target_dbfs = params.get("target_dbfs", -25.0)
            return segment.apply_gain(target_dbfs - segment.dBFS)
        return segment

@dataclass
class STTService(BaseService):
    model_size: str = "tiny"
    device: Optional[str] = None
    force_transcribe: bool = False

    def run(self, context: StepContext) -> Dict[str, Any]:
        params = {
            "model_size": self.model_size,
            "device": self.device,
            "force_transcribe": self.force_transcribe,
        }
        params.update({k: v for k, v in context.settings.items() if v is not None})

        existing = context.artifacts.get("transcripts")
        if existing and not params.get("force_transcribe"):
            logger.info("Transcripts already present; skipping STT step.")
            context.ensure_step_store()["transcripts"] = existing
            return {"transcripts": existing}

        chunk_list = list(context.artifacts.get("chunks") or [])
        has_chunks = bool(chunk_list)
        targets: Iterable[str] = chunk_list if has_chunks else [str(context.asset.resolved_path())]

        transcripts: List[Dict[str, Any]] = []
        for idx, path in enumerate(list(targets)):
            text = ""
            try:
                text = speech_to_text(
                    path,
                    model_size=params.get("model_size", self.model_size),
                    device=params.get("device", self.device),
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("Transcription failed for %s: %s", path, exc)
            new_path = path
            if has_chunks:
                new_path = str(self._rename_chunk(Path(path), text, idx))
                chunk_list[idx] = new_path
                # 将文件重命名为新文件名
                try:
                    os.rename(path, new_path)
                except OSError:
                    logger.warning("Failed to rename chunk %s to %s", path, new_path)
            transcripts.append({"file": new_path, "text": text})

        context.artifacts["transcripts"] = transcripts
        if has_chunks:
            context.artifacts["chunks"] = chunk_list
        context.ensure_step_store()["transcripts"] = transcripts
        return {"transcripts": transcripts}

    @staticmethod
    def _rename_chunk(path: Path, text: str, index: int) -> Path:
        snippet = (text or "").strip()
        if not snippet:
            return path
        truncated = snippet[:50]
        sanitized = re.sub(r"[\\/:*?\"<>|]", "", truncated)
        sanitized = re.sub(r"\s+", "_", sanitized).strip("_")
        if not sanitized:
            return path
        new_name = f"{index:04d}_{sanitized}.wav"
        new_path = path.with_name(new_name)
        try:
            if new_path.exists():
                return new_path
            path.rename(new_path)
            return new_path
        except OSError:
            return path


@dataclass
class PlaybackService(BaseService):
    repeats: int = 1
    initial_repeats: Optional[int] = None
    initial_threshold: Optional[int] = None
    translate: bool = False
    play_audio_flag: bool = True
    skip_first: bool = False
    fs_multi: float = 1.0

    def run(self, context: StepContext) -> Dict[str, Any]:
        params = self._merge_params(context.settings)
        chunk_paths = list(context.artifacts.get("chunks") or [])
        if not chunk_paths:
            chunk_paths = [str(context.asset.resolved_path())]

        start_file = params.get("start_file")
        start_idx = 0
        if start_file:
            for idx, path in enumerate(chunk_paths):
                if Path(path).name == Path(start_file).name:
                    start_idx = idx
                    break

        callback = context.get_callback("on_progress")
        transcripts = context.artifacts.get("transcripts") or []
        transcript_map = {Path(item["file"]).name: item.get("text", "") for item in transcripts if isinstance(item, dict)}

        played_segments = 0
        playback_seconds = 0.0
        total_segments = len(chunk_paths[start_idx:])
        last_played = None
        translations: List[Dict[str, Any]] = []
        session_limit = context.settings.get("max_session_seconds")
        limit_seconds: Optional[float] = None
        try:
            limit_seconds = float(session_limit)
        except (TypeError, ValueError):
            limit_seconds = None

        for offset, path in enumerate(chunk_paths[start_idx:], start=start_idx):
            if limit_seconds is not None and playback_seconds >= limit_seconds:
                logger.info(
                    "Reached playback time limit %.2fs for asset %s; stopping session.",
                    limit_seconds,
                    context.asset.id,
                )
                break
            if params.get("skip_first") and offset == start_idx:
                logger.info("Skipping first segment per configuration.")
                continue

            repeats = params.get("repeats", 1)
            threshold = params.get("initial_threshold")
            initial_repeats = params.get("initial_repeats")
            params["fs_multi"] = 0.8*self.fs_multi if context.asset.lang == "en" else self.fs_multi
            if (
                threshold is not None
                and initial_repeats is not None
                and (offset - start_idx) < int(threshold)
            ):
                repeats = int(initial_repeats)

            file_name = Path(path).name
            words_len = len(file_name.split("_"))-1
            transcript_text = transcript_map.get(file_name, "")

            if callback:
                callback(file_name, offset)

            segment_seconds = self._segment_duration_seconds(path)
            translation_text = None
                    
            logger.info("Translation result for %s: %s", path, translation_text)
            # 针对英文文本，如果只有单词的话取消重复播放
            if (context.asset.lang or "").lower().startswith("en") and words_len == 1:
                repeat_count = 1
            else:
                repeat_count = repeats
                if params.get("translate") and transcript_text:
                    translation_text = self._translate(transcript_text)
                    if translation_text:
                        translations.append({"file": path, "translation": translation_text})

            for idx in range(repeat_count):
                self._play(path, params)
                playback_seconds += segment_seconds
                if translation_text and idx == 0 and repeat_count>1:
                    try:
                        time.sleep(1.5)
                        speak_text(translation_text, play_audio_flag=self.play_audio_flag)
                    except Exception as exc:  # pragma: no cover
                        logger.warning("Speak translation failed: %s", exc)
                time.sleep(0.6+words_len*0.25)

            played_segments += 1
            last_played = path

        playback_result = {
            "last_played": last_played,
            "segments_total": total_segments,
            "segments_played": played_segments,
            "translations": translations,
            "seconds_played": playback_seconds,
            "seconds_limit": limit_seconds,
        }
        context.artifacts["playback"] = playback_result
        return playback_result

    def _merge_params(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        params = {
            "repeats": self.repeats,
            "initial_repeats": self.initial_repeats,
            "initial_threshold": self.initial_threshold,
            "translate": self.translate,
            "skip_first": self.skip_first,
            "fs_multi": self.fs_multi,
        }
        params.update({k: v for k, v in overrides.items() if v is not None})
        return params

    def _play(self, path: str, params: Dict[str, Any]) -> None:
        try:
            play_audio(path, fs_multi=float(params.get("fs_multi", 1.0)))
        except Exception as exc:  # pragma: no cover
            logger.warning("Playback failed for %s: %s", path, exc)

    def _translate(self, text: str) -> Optional[str]:
        if not traslate_text:
            return None
        try:
            return traslate_text(text)
        except Exception as exc:  # pragma: no cover
            raise Exception("Translation failed: %s", exc)
            return None

    @staticmethod
    def _segment_duration_seconds(path: str) -> float:
        try:
            info = sf.info(path)
            return float(info.duration)
        except Exception:  # pragma: no cover
            logger.warning("Failed to get duration for %s", path)
            return 0.0
