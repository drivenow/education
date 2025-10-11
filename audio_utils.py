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

def play_audio(audio_file, fs_multi=1):
    # 音量的放大倍数
    logger.info("Playing audio file: {}".format(audio_file))
    sps, audio = wavfile.read(audio_file)
    sd.play(audio, sps*fs_multi, blocking=True)  # Samples per second

@retry(stop_max_attempt_number=3, wait_fixed=1000)
def write_audio(audio_file, audio):
    wavfile.write(audio_file, audio[0], audio[1])



if __name__=="__main__":
    audio_file = "C:\\Users\\fullmetal\\Desktop\\乐乐\\苏杰学习材料\\新思维1AMp3音频\\新思维1AMp3音频\\NWTEG_PB1A_Ch1_C\\chunk0.wav"
    play_audio(audio_file)

