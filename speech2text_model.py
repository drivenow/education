from logger import logger
import os
import whisper
import time

asr = None
whisper_model = None

def speech_to_text_old(audio_file):
    import paddle
    global asr
    from paddlespeech.cli.st import STExecutor
    from paddlespeech.cli.asr.infer import ASRExecutor
    if not asr:
        asr = ASRExecutor()  # 语音转文本
    result = asr(audio_file=audio_file, model="transformer_librispeech", lang="en", codeswitch = False)  # 录音文件地址
    logger.info(result)
    return result

def speech_to_text(audio_file):
    global whisper_model
    t1 = time.time()
    if not whisper_model:
        whisper_model = whisper.load_model("small", device="cuda")
        print("Whisper模型加载耗时：", time.time() - t1)

    result = whisper_model.transcribe(audio_file, initial_prompt="以下为简单的英文句子")
    result= "".join([i["text"] for i in result["segments"] if i is not None]).strip(). \
        replace("?", "").replace("!", "").replace(".", ""). \
        replace(",", " ").replace(".", "").replace(";", ""). \
        replace(":", "")
    logger.info("speech_to_text: {}".format(result))
    return result


if   __name__ == '__main__':
    audio_file = "C:\\Users\\fullmetal\\Desktop\\乐乐\\苏杰学习材料\\新思维1AMp3音频\\新思维1AMp3音频\\NWTEG_PB1A_Ch7_Reading\\f16_here is a birthday cake for you.wav"
    assert os.path.exists(audio_file), "11"

    result = speech_to_text(audio_file)
    print(result)


