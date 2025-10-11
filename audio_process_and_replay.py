import os
from logger import logger
import subprocess
from pydub import AudioSegment
from pydub.silence import split_on_silence
from audio_utils import resample_audio, play_audio
from speech2text_model import speech_to_text
from translate_model import traslate_text
from speaker_model import speak_text
from natsort import natsorted
import time
import re
import streamlit as st


def contains_japanese(text):
    # 定义日文字符的正则表达式
    japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\uFF66-\uFF9F]')

    # 如果匹配到日文字符则返回 True
    return bool(japanese_pattern.search(text))

# Define a function to normalize a chunk to a target amplitude.
def match_target_amplitude(aChunk, target_dBFS):
    ''' Normalize given audio chunk '''
    change_in_dBFS = target_dBFS - aChunk.dBFS
    return aChunk.apply_gain(change_in_dBFS)

def split_audio(audio_file, target_dir, min_silence_len=500, silence_thresh=16, bitrate="128k"):
    # Split track where the silence is 2 seconds or more and get chunks using
    # the imported function.
    if os.path.exists(target_dir) and len(os.listdir(target_dir))>5:
        logger.info("文件已生成，无需再生成")
        return
    if audio_file.endswith(".mp3"):
        song = AudioSegment.from_mp3(audio_file)
    elif audio_file.endswith(".wav"):
        song = AudioSegment.from_wav(audio_file)
    elif audio_file.endswith(".m4a"):
        song = AudioSegment.from_file(audio_file, "m4a")
    else:
        logger.error("Unsupported file format.")
        raise ValueError("Unsupported file format.")

    chunks = split_on_silence (
        # Use the loaded audio.
        song,
        # Specify that a silent chunk must be at least 2 seconds or 2000 ms long.
        min_silence_len = min_silence_len,
        # Consider a chunk silent if it's quieter than -16 dBFS.
        # (You may want to adjust this parameter.)
        silence_thresh = song.dBFS - silence_thresh
    )

    # Process each chunk with your parameters
    for i, chunk in enumerate(chunks):
        # Normalize the entire chunk.
        silence_chunk = AudioSegment.silent(duration=500)
        normalized_chunk = match_target_amplitude(silence_chunk+chunk, -25.0)

        # Export the audio chunk with new bitrate.
        split_autio_file = os.path.join(target_dir, "chunk{0}.wav".format(i))
        normalized_chunk.export(
            split_autio_file,
            bitrate = bitrate,
            format = "wav"
        )

        resample_audio(split_autio_file, sr=16000)#降低频率
        text = speech_to_text(split_autio_file)
        words_num = len(text.split())
        if not text:
            text = str(i)

        # Create a silence chunk that's 0.5 seconds (or 500 ms) long for padding.
        silence_chunk_end = AudioSegment.silent(duration=300*(words_num))

        # Add the padding chunk to beginning and end of the entire chunk.
        audio_chunk =  chunk + silence_chunk_end
        audio_chunk.export(
            split_autio_file,
            bitrate = bitrate,
            format = "wav"
        )
        os.rename(split_autio_file, os.path.join(target_dir, "f{0}_{1}.wav".format(i, text)))
        logger.info(f"Exporting f{0}_{1}.wav".format(i, text))

    return True


def replay_single_audio(file_path, repeats = 10, translate=True, audio_file = ""):
    global model
    number_list = [str(i) for i in list(range(200))]
    filter_list = set(["", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "HELLO", "HI", "HIYA",
                  "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
                 "picture one", "picture two", "picture too", "picture three", "picture four", "picture five", "picture six", "picture seven", "picture eight", "picture nine", "picture ten",
              "pictures one", "pictures two", "pictures too", "pictures three", "pictures four", "pictures five", "pictures six", "pictures seven", "pictures eight", "pictures nine", "pictures ten",
                       "now you try", "here is an example", "read and find out", "thank you",  "goodbye", "good bye", "see you later", "see you soon", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night", "good night",
                       "nonsense", "keywords"
                       ]+number_list)
    filter_list = [i.upper() for i in filter_list]
    file_name = os.path.basename(file_path)
    if file_name.endswith(".wav"):
        time.sleep(1.5)
        logger.info("replay_audio {}: {}".format(file_name.split(".")[0].split("_")[0], file_name))
        name = file_name.split(".")[0].split("_")[1]
        if "chapt" in name or name.strip().upper() in filter_list or \
                len(name.replace(" ", ""))<6:#and not "字母" in audio_file
            sub_repeats = 1
        else:
            sub_repeats = repeats
        for i in range(1, sub_repeats + 1):
            if translate:
                # 翻译并朗读中文
                translated_name = traslate_text(name)
                if i == 2 and not contains_japanese(translated_name):
                    speak_text(translated_name)
                    time.sleep(1)
            play_audio(file_path)



def main_split_and_replay_audio(audio_file, num_repeats=1, translate = True):
    target_dir = os.path.join(os.path.dirname(audio_file), audio_file.split(".")[0])
    os.makedirs(target_dir, exist_ok=True)
    split_audio(audio_file, target_dir)
    print("target_dir: ", target_dir)
    # 逐个循环播放音频文件，每个文件播放完毕后暂停1秒钟
    files = natsorted(os.listdir(target_dir))
    for fidx, file_name in enumerate(files):
        if fidx == 0:
            continue
        if fidx < 3:
            repeats = 1
        else:
            repeats = num_repeats
        replay_single_audio(os.path.join(target_dir, file_name), repeats = repeats, translate=translate, audio_file = audio_file)


if __name__ == '__main__':
    # Load your audio.
    eglish_dir = "C:/Users/fullmetal/Desktop/乐乐/苏杰学习材料/新思维1AMp3音频/新思维1AMp3音频/"
    eglish_dir_1b = "C:/Users/fullmetal/Desktop/乐乐/新思维小学英语1B听力/NWTE GOLD_1B"
    fname = "NWTEG_PB1A_Ch1_A.mp3"  # 播放的文件
    audio_file = os.path.join(eglish_dir, fname)
    audio_file1 = "D:/Wondershare/ExportFiles/1A主题复习.wav"
    audio_file2 = "D:/Wondershare/ExportFiles/主题复习2.wav"
    audio_file3 = "D:/Wondershare/ExportFiles/主题复习3.wav"
    audio_file4 = os.path.join(eglish_dir, "24-25（上）一年级英语字母发音练习音频01.m4a")
    audio_file5 = os.path.join(eglish_dir, "24-25（上）一年级英语字母发音练习音频02.m4a")
    audio_file6 = os.path.join(eglish_dir, "24-25（上）一年级英语字母发音练习音频03.m4a")
    audio_file7 = os.path.join(eglish_dir, "24-25（上）一年级英语字母发音练习音频04.m4a")
    audio_file8 = os.path.join(eglish_dir, "24-25（上）一年级字母发音练习音频05.m4a")

    # 获取当前是周几
    today = time.strftime("%a", time.localtime())
    # 周一到周五播放音频
    if today == "Mon":
        file_list = [ "NWTEG_PB1A_Ch1_A.mp3", "NWTEG_PB1A_Ch1_B.mp3", "NWTEG_PB1A_Ch1_C.mp3", "NWTEG_PB1A_Ch1_E.mp3", "NWTEG_PB1A_Ch1_F.mp3", "NWTEG_PB1A_Ch1_Phonics.mp3"][::-1]+[audio_file4]
        file_list = [audio_file4]+["NWTEG_PB1B_Ch1_A.mp3",  "NWTEG_PB1B_Ch1_C.mp3", "NWTEG_PB1B_Ch1_D.mp3", "NWTEG_PB1B_Ch1_B.mp3",]
    elif today == "Tue":
        file_list = ["NWTEG_PB1A_Ch2_A.mp3", "NWTEG_PB1A_Ch2_B.mp3", "NWTEG_PB1A_Ch2_C.mp3", "NWTEG_PB1A_Ch2_E.mp3", "NWTEG_PB1A_Ch2_F_Song.mp3", "NWTEG_PB1A_Ch2_Phonics.mp3"][::-1]+[audio_file5]
        file_list = [audio_file5]+[ "NWTEG_PB1B_Ch1_C.mp3", "NWTEG_PB1B_Ch1_D.mp3", "NWTEG_PB1B_Ch1_B.mp3", "NWTEG_PB1B_Ch1_A.mp3", ]
    elif today == "Wed":
        file_list = [audio_file6]+["NWTEG_PB1A_Ch3_A.mp3", "NWTEG_PB1A_Ch3_B.mp3", "NWTEG_PB1A_Ch3_C.mp3", "NWTEG_PB1A_Ch3_E.mp3", "NWTEG_PB1A_Ch3_F_Song.mp3", "NWTEG_PB1A_Ch3_Phonics.mp3"][::-1]
        file_list = [audio_file6]+[ "NWTEG_PB1B_Ch1_C.mp3", "NWTEG_PB1B_Ch1_D.mp3", "NWTEG_PB1B_Ch1_B.mp3", "NWTEG_PB1B_Ch1_A.mp3", ]
    elif today == "Thu":
        file_list = [audio_file7]+["NWTEG_PB1A_Ch4_A.mp3", "NWTEG_PB1A_Ch4_B.mp3", "NWTEG_PB1A_Ch4_C.mp3", "NWTEG_PB1A_Ch4_E.mp3", "NWTEG_PB1A_Ch4_F.mp3", "NWTEG_PB1A_Ch4_Phonics.mp3"][::-1]
        file_list = [audio_file7]+["NWTEG_PB1B_Ch2_A.mp3",  "NWTEG_PB1B_Ch2_C.mp3", "NWTEG_PB1B_Ch2_D.mp3", "NWTEG_PB1B_Ch2_B.mp3",]
    elif today == "Fri":
        file_list = [audio_file8]+["NWTEG_PB1A_Ch5_A.mp3", "NWTEG_PB1A_Ch5_B.mp3", "NWTEG_PB1A_Ch5_C.mp3", "NWTEG_PB1A_Ch5_E.mp3", "NWTEG_PB1A_Ch5_F.mp3", "NWTEG_PB1A_Ch5_Phonics.mp3"][::-1]
        file_list = [audio_file8]+["NWTEG_PB1B_Ch2_A.mp3",  "NWTEG_PB1B_Ch2_C.mp3", "NWTEG_PB1B_Ch2_D.mp3", "NWTEG_PB1B_Ch2_B.mp3",]
    else:
        file_list = [audio_file8]+["NWTEG_PB1A_Ch1_A.mp3", "NWTEG_PB1A_Ch1_B.mp3", "NWTEG_PB1A_Ch1_C.mp3", "NWTEG_PB1A_Ch6_E.mp3", "NWTEG_PB1A_Ch6_F_Song.mp3", "NWTEG_PB1A_Ch6_Phonics.mp3"][::-1]

    # file_list = ["NWTEG_PB1A_Ch6_E.mp3"]

    for audio_file in file_list:
        logger.info(audio_file)
        if audio_file.startswith("NWTEG_PB1A") or audio_file.startswith("The Biscuits"):
            audio_file = os.path.join(eglish_dir, audio_file)
        elif audio_file.startswith("NWTEG_PB1B"):
            audio_file = os.path.join(eglish_dir_1b, audio_file)
        if "字母发音" in audio_file:
            main_split_and_replay_audio(audio_file, num_repeats=1, translate = True)
        elif "song" in audio_file:
            main_split_and_replay_audio(audio_file, num_repeats=1, translate = False)
        else:
            main_split_and_replay_audio(audio_file, num_repeats=2, translate = True)
        # main_split_and_replay_audio(audio_file, num_repeats=1, translate = False)