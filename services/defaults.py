from __future__ import annotations

import os
from pathlib import Path
import re
import time
from typing import Any

from natsort import natsorted
from pydub import AudioSegment
from pydub.silence import split_on_silence

from audio_utils import play_audio, resample_audio
from logger import logger
from speech2text_model import speech_to_text
from translate_model import traslate_text

from services.base import BaseService, StepContext


class AudioSplitterService:
    def __init__(self, options: dict[str, Any]):
        self.options = options

    def setup(self) -> None:
        pass

    def execute(self, ctx: StepContext, params: dict) -> StepContext:
        asset = ctx["asset"]
        source_path = Path(asset.source_uri)
        target_dir = source_path.with_suffix("")
        target_dir.mkdir(exist_ok=True, parents=True)
        existing_chunks = sorted(target_dir.glob("*.wav"))
        if len(existing_chunks) > 5:
            logger.info("音频 %s 已存在切分结果，跳过重新生成。", source_path.name)
            artifacts = ctx.setdefault("artifacts", {})
            artifacts["split"] = {"target_dir": str(target_dir)}
            artifacts["chunks"] = [str(path) for path in existing_chunks]
            return ctx
        min_silence_len = params.get("min_silence_len", self.options.get("min_silence_len", 500))
        silence_thresh = params.get("silence_thresh", self.options.get("silence_thresh", 16))
        bitrate = params.get("bitrate", self.options.get("bitrate", "128k"))

        audio = self._load_audio(source_path)
        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=audio.dBFS - silence_thresh,
        )
        label_with_stt = params.get(
            "label_with_stt", self.options.get("label_with_stt", True)
        )
        model_size = params.get("model_size") or self.options.get("model_size", "small")
        device = params.get("device") or self.options.get("device")

        for i, chunk in enumerate(chunks):
            silence_chunk = AudioSegment.silent(duration=500)
            normalized_chunk = self._match_target_amplitude(silence_chunk + chunk, -25.0)

            split_audio_file = target_dir / f"chunk{i}.wav"
            normalized_chunk.export(
                split_audio_file,
                bitrate=bitrate,
                format="wav",
            )

            resample_audio(str(split_audio_file), sr=16000)
            text = ""
            if label_with_stt:
                text = speech_to_text(
                    str(split_audio_file), model_size=model_size, device=device
                )
            words_num = len(text.split()) if text else 0
            if not text:
                text = str(i)

            silence_chunk_end = AudioSegment.silent(duration=300 * words_num)
            audio_chunk = chunk + silence_chunk_end
            audio_chunk.export(
                split_audio_file,
                bitrate=bitrate,
                format="wav",
            )
            final_path = target_dir / f"f{i}_{text}.wav"
            split_audio_file.rename(final_path)

        artifacts = ctx.setdefault("artifacts", {})
        artifacts["split"] = {"target_dir": str(target_dir)}
        artifacts["chunks"] = [
            os.path.join(str(target_dir), name)
            for name in natsorted(os.listdir(target_dir))
            if name.endswith(".wav")
        ]
        return ctx

    def teardown(self) -> None:
        pass

    @staticmethod
    def _load_audio(path: Path) -> AudioSegment:
        if path.suffix.lower() == ".mp3":
            return AudioSegment.from_mp3(path)
        if path.suffix.lower() == ".wav":
            return AudioSegment.from_wav(path)
        if path.suffix.lower() == ".m4a":
            return AudioSegment.from_file(path, "m4a")
        raise ValueError(f"Unsupported file format: {path}")

    @staticmethod
    def _match_target_amplitude(audio_segment: AudioSegment, target_dbfs: float) -> AudioSegment:
        change = target_dbfs - audio_segment.dBFS
        return audio_segment.apply_gain(change)


class WhisperSTTService:
    def __init__(self, options: dict[str, Any]):
        self.options = options

    def setup(self) -> None:
        pass

    def execute(self, ctx: StepContext, params: dict) -> StepContext:
        artifacts = ctx.setdefault("artifacts", {})
        chunk_paths = artifacts.get("chunks", [])
        transcripts: list[dict[str, str]] = []
        model_size = params.get("model_size") or self.options.get("model_size", "small")
        device = params.get("device") or self.options.get("device")

        for chunk_path in chunk_paths:
            text = self._extract_from_filename(chunk_path)
            if not text or params.get("force_transcribe", False):
                text = speech_to_text(chunk_path, model_size=model_size, device=device)
            transcripts.append({"file": chunk_path, "text": text})

        artifacts["transcripts"] = transcripts
        return ctx

    def teardown(self) -> None:
        pass

    @staticmethod
    def _extract_from_filename(path: str) -> str:
        name = Path(path).stem
        parts = name.split("_", 1)
        if len(parts) == 2:
            return parts[1]
        return ""


class TranslatorService:
    def __init__(self, options: dict[str, Any]):
        self.options = options

    def setup(self) -> None:
        pass

    def execute(self, ctx: StepContext, params: dict) -> StepContext:
        artifacts = ctx.setdefault("artifacts", {})
        transcripts = artifacts.get("transcripts", [])
        if not transcripts:
            logger.warning("Translator step skipped because transcripts are missing.")
            return ctx

        translations: list[dict[str, str]] = []
        for item in transcripts:
            translated = traslate_text(item["text"])
            translations.append({"file": item["file"], "text": item["text"], "translation": translated})

        artifacts["translations"] = translations
        return ctx

    def teardown(self) -> None:
        pass


class TextToSpeechService:
    def __init__(self, options: dict[str, Any]):
        self.options = options

    def setup(self) -> None:
        pass

    def execute(self, ctx: StepContext, params: dict) -> StepContext:
        artifacts = ctx.setdefault("artifacts", {})
        source = artifacts.get("translations") or artifacts.get("transcripts", [])
        if not source:
            logger.warning("TTS step skipped because no text source is available.")
            return ctx

        output_dir = Path(
            params.get("output_dir", self.options.get("output_dir", Path("speaking_outputs")))
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        generated_files = []
        for index, item in enumerate(source):
            text = item.get("translation") or item.get("text")
            save_path = output_dir / f"{ctx['asset'].id}_{index}.wav"
            self._speak_text(text, str(save_path), params.get("play_audio", False))
            generated_files.append(str(save_path))

        artifacts["tts_outputs"] = generated_files
        return ctx

    def teardown(self) -> None:
        pass


class PlaybackService:
    def __init__(self, options: dict[str, Any]):
        self.options = options

    def setup(self) -> None:
        pass

    def execute(self, ctx: StepContext, params: dict) -> StepContext:
        artifacts = ctx.setdefault("artifacts", {})
        chunk_paths = artifacts.get("chunks", [])
        if not chunk_paths:
            logger.warning("Playback skipped because no chunks were generated.")
            return ctx

        asset = ctx["asset"]
        callbacks = ctx.get("callbacks", {})
        on_progress = callbacks.get("on_progress")

        start_file = params.get("start_file") or self.options.get("start_file")
        translate = params.get("translate", self.options.get("translate", True))
        repeats = params.get("repeats", self.options.get("repeats", 1))
        initial_repeats = params.get(
            "initial_repeats", self.options.get("initial_repeats", 1)
        )
        skip_first = params.get("skip_first", self.options.get("skip_first", True))
        initial_threshold = params.get(
            "initial_threshold", self.options.get("initial_threshold", 3)
        )

        start_index = 0
        if start_file:
            for idx, path in enumerate(chunk_paths):
                if Path(path).name == start_file:
                    start_index = idx
                    break

        last_played = None
        for idx, path in enumerate(chunk_paths):
            if idx == 0 and skip_first:
                continue
            if idx < start_index:
                continue

            repeat_times = initial_repeats if idx < initial_threshold else repeats
            if repeat_times <= 0:
                continue

            if callable(on_progress):
                on_progress(Path(path).name, idx)

            self._replay_single_audio(path, repeat_times, translate, asset.source_uri)
            last_played = Path(path).name

        artifacts["playback"] = {
            "last_played": last_played,
            "translate": translate,
            "repeats": repeats,
        }
        return ctx

    def teardown(self) -> None:
        pass

    @staticmethod
    def _speak_text(text: str, save_file: str | None, play_audio_flag: bool) -> None:
        from speaker_model import speak_text as do_speak_text  # local import to avoid heavy deps when unused

        kwargs: dict[str, Any] = {"play_audio_flag": play_audio_flag}
        if save_file is not None:
            kwargs["save_file"] = save_file
        do_speak_text(text, **kwargs)

    @staticmethod
    def _contains_japanese(text: str) -> bool:
        japanese_pattern = re.compile(r"[\u3040-\u309F\u30A0-\u30FF\uFF66-\uFF9F]")
        return bool(japanese_pattern.search(text))

    def _replay_single_audio(self, file_path: str, repeats: int, translate: bool, audio_file: str) -> None:
        number_list = [str(i) for i in list(range(200))]
        filter_list = set(
            [
                "",
                "ONE",
                "TWO",
                "THREE",
                "FOUR",
                "FIVE",
                "SIX",
                "SEVEN",
                "EIGHT",
                "NINE",
                "TEN",
                "HELLO",
                "HI",
                "HIYA",
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "G",
                "H",
                "I",
                "J",
                "K",
                "L",
                "M",
                "N",
                "O",
                "P",
                "Q",
                "R",
                "S",
                "T",
                "U",
                "V",
                "W",
                "X",
                "Y",
                "Z",
                "picture one",
                "picture two",
                "picture too",
                "picture three",
                "picture four",
                "picture five",
                "picture six",
                "picture seven",
                "picture eight",
                "picture nine",
                "picture ten",
                "pictures one",
                "pictures two",
                "pictures too",
                "pictures three",
                "pictures four",
                "pictures five",
                "pictures six",
                "pictures seven",
                "pictures eight",
                "pictures nine",
                "pictures ten",
                "now you try",
                "here is an example",
                "read and find out",
                "thank you",
                "goodbye",
                "good bye",
                "see you later",
                "see you soon",
                "good night",
                "nonsense",
                "keywords",
                *number_list,
            ]
        )
        filter_list = {item.upper() for item in filter_list}

        file_name = os.path.basename(file_path)
        if file_name.endswith(".wav"):
            time.sleep(0.1)
            logger.info("replay_audio %s: %s", file_name.split(".")[0].split("_")[0], file_name)
            name = file_name.split(".")[0].split("_")[1]
            if (
                "chapt" in name
                or name.strip().upper() in filter_list
                or len(name.replace(" ", "")) < 6
            ):
                sub_repeats = 1
            else:
                sub_repeats = repeats

            for i in range(1, sub_repeats + 1):
                if translate:
                    translated_name = traslate_text(name)
                    if i == 2 and not self._contains_japanese(translated_name):
                        self._speak_text(translated_name, save_file=None, play_audio_flag=True)
                        time.sleep(0.1)
                play_audio(file_path)


def create_splitter(options: dict[str, Any]) -> BaseService:
    return AudioSplitterService(options)


def create_stt(options: dict[str, Any]) -> BaseService:
    return WhisperSTTService(options)


def create_translator(options: dict[str, Any]) -> BaseService:
    return TranslatorService(options)


def create_tts(options: dict[str, Any]) -> BaseService:
    return TextToSpeechService(options)


def create_playback(options: dict[str, Any]) -> BaseService:
    return PlaybackService(options)
