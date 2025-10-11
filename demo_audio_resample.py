import librosa
import numpy as np
import soundfile as sf


def change_audio_pitch(y, sr, target_freq, current_freq):
    """
    将音频的频率调整到目标频率

    参数:
    - y: 音频数据 (numpy array)
    - sr: 采样率 (sample rate)
    - target_freq: 目标频率 (目标频率)
    - current_freq: 当前频率 (音频的原始频率)

    返回:
    - 调整后的音频数据
    """
    # 计算频率比率
    freq_ratio = target_freq / current_freq

    # 使用 librosa 的 pitch_shift 方法进行音调变换
    y_shifted = librosa.effects.pitch_shift(y, sr, np.log2(freq_ratio))

    return y_shifted


# 加载音频文件
audio_path = "C:\\Users\\fullmetal\\Desktop\\乐乐\\苏杰学习材料\\新思维1AMp3音频\\新思维1AMp3音频\\NWTEG_PB1A_Ch1_A\\chunk6.wav"
audio_path = "output_audio.wav"
y, sr = librosa.load(audio_path, sr=16000)


# 保存处理后的音频
output_path = "output_audio.wav"
sf.write(output_path, y, sr)

