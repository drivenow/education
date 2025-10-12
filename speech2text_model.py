from __future__ import annotations

import os
import time
from typing import Dict, Tuple

import whisper
from logger import logger

asr = None
_whisper_cache: Dict[Tuple[str, str], whisper.Whisper] = {}


def speech_to_text_old(audio_file: str):
    import paddle
    global asr
    from paddlespeech.cli.st import STExecutor
    from paddlespeech.cli.asr.infer import ASRExecutor

    if not asr:
        asr = ASRExecutor()  # 语音转文本
    result = asr(
        audio_file=audio_file, model="transformer_librispeech", lang="en", codeswitch=False
    )  # 录音文件地址
    logger.info(result)
    return result


def speech_to_text(audio_file: str, model_size: str = "small", device: str | None = None) -> str:
    model = _get_whisper_model(model_size, device)
    result = model.transcribe(audio_file, initial_prompt="以下为简单的英文句子")
    text = (
        "".join([segment["text"] for segment in result["segments"] if segment is not None])
        .strip()
        .replace("?", "")
        .replace("!", "")
        .replace(".", "")
        .replace(",", " ")
        .replace(";", "")
        .replace(":", "")
    )
    logger.info("speech_to_text(%s): %s", model_size, text)
    return text


def _get_whisper_model(model_size: str, device: str | None) -> whisper.Whisper:
    resolved_device = device or _default_device()
    cache_key = (model_size, resolved_device)
    if cache_key in _whisper_cache:
        return _whisper_cache[cache_key]

    t1 = time.time()
    model = whisper.load_model(model_size, device=resolved_device)
    duration = time.time() - t1
    print(f"Whisper模型({model_size}, device={resolved_device})加载耗时：{duration:.2f}s")
    _whisper_cache[cache_key] = model
    return model


def _default_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


if __name__ == "__main__":
    audio_file = "C:\\Users\\fullmetal\\Desktop\\乐乐\\苏杰学习材料\\新思维1AMp3音频\\新思维1AMp3音频\\NWTEG_PB1A_Ch7_Reading\\f16_here is a birthday cake for you.wav"
    assert os.path.exists(audio_file), "11"

    result = speech_to_text(audio_file, model_size="tiny")
    print(result)
