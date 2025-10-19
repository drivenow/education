import librosa
import numpy as np
import soundfile as sf
from scipy.io import wavfile
import sys
import sounddevice as sd
from logger import logger
from retrying import retry

def format_folder_name(folder_name):
    folder_name = folder_name.strip(). \
        replace("?", "").replace("*", "").replace("<", ""). \
        replace(",", " ").replace(".", "").replace(";", ""). \
        replace(":", "").replace(">", "").replace("|", "").replace("\"", "")
    return folder_name
def resample_audio(audio_path, sr=16000):
    y, sr = librosa.load(audio_path, sr=sr)
    sf.write(audio_path, y, sr)

# def play_audio(audio_file, fs_multi=1):
#     # 音量的放大倍数
#     logger.info("Playing audio file: {}".format(audio_file))
#     sps, audio = wavfile.read(audio_file)
#     sd.play(audio, sps*fs_multi, blocking=True)  # Samples per second


def play_audio(audio_file, fs_multi=1.0, gain=1.5, gain_db=None):
    """
    播放音频文件，可调整采样率和增益。

    参数:
    audio_file (str): 音频文件路径。
    fs_multi (float, 可选): 采样率倍数，默认1.0。
    gain (float, 可选): 增益倍数，默认1.0。
    gain_db (float, 可选): 增益 dB 值，默认None。
    """
    sps, audio = wavfile.read(audio_file)

    # 到 float32，范围 [-1, 1]
    if np.issubdtype(audio.dtype, np.integer):
        x = audio.astype(np.float32) / np.iinfo(audio.dtype).max
    else:
        x = audio.astype(np.float32)

    # 增益：优先用 dB
    if gain_db is not None:
        gain = 10 ** (gain_db / 20.0)
    y = np.clip(x * float(gain), -1.0, 1.0)  # 简单限幅避免削顶

    sd.play(y, int(sps * fs_multi), blocking=True)

@retry(stop_max_attempt_number=3, wait_fixed=1000)
def write_audio(audio_file, audio):
    wavfile.write(audio_file, audio[0], audio[1])



if __name__=="__main__":
    audio_file = "X:\BaiduNetdiskDownload\\0001_What's_your_name.wav"
    play_audio(audio_file)

