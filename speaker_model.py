import os
import sys
sys.path.append("D:/voice/")
sys.path.append("D:/voice/VITStuning")
from logger import logger
import torch
import re
from torch import no_grad, LongTensor
import VITStuning.commons
import VITStuning.utils
from VITStuning.models import SynthesizerTrn
from VITStuning.text import text_to_sequence
from audio_utils import write_audio, play_audio, format_folder_name
from pydub import AudioSegment
import gradio
import librosa

vits_net_g = None
vits_hps = None
vits_speaker_ids = None
tts_fn = None
device = "cuda:0" if torch.cuda.is_available() else "cpu"

language_marks = {
    "Japanese": "",
    "日本語": "[JA]",
    "简体中文": "[ZH]",
    "English": "[EN]",
    "Mix": "",
}
lang = ['日本語', '简体中文', 'English', 'Mix']
def get_text(text, hps, is_symbol):
    text_norm = text_to_sequence(text, hps.symbols, [] if is_symbol else hps.data.text_cleaners)
    if hps.data.add_blank:
        text_norm = VITStuning.commons.intersperse(text_norm, 0)
    text_norm = LongTensor(text_norm)
    return text_norm


def create_tts_fn(model, hps, speaker_id, speed = 0.8):
    def tts_fn(text, language = "简体中文"):
        """
        :param text: 输入的文本
        :param speaker: 说话人名称
        :param language: 语言名称
        :param speed: 语音生成速度
        :return:
        """
        if language is not None:
            text = language_marks[language] + text + language_marks[language]
        stn_tst = get_text(text, hps, False)
        with no_grad():
            x_tst = stn_tst.unsqueeze(0).to(device)
            x_tst_lengths = LongTensor([stn_tst.size(0)]).to(device)
            sid = LongTensor([speaker_id]).to(device)
            audio = model.infer(x_tst, x_tst_lengths, sid=sid, noise_scale=.667, noise_scale_w=0.8,
                                length_scale=1.0 / speed)[0][0, 0].data.cpu().float().numpy()
        del stn_tst, x_tst, x_tst_lengths, sid
        return "Success", (hps.data.sampling_rate, audio)

    return tts_fn


def create_model(role_id = 0):
    roles = ["QD", "shen"]
    speeds = [0.9, 0.9, 1.0]
    rint = role_id#randint(100)
    # if rint == 0:
        # config_dir = "D:/voice/VITStuning/OUTPUT_MODEL/config.json"
        # model_dir = "D:/voice/VITStuning/OUTPUT_MODEL/G_latest.pth"
    config_dir = "D:/voice/VITStuning/OUTPUT_MODEL_SJL/config.json"
    model_dir = "D:/voice/VITStuning/OUTPUT_MODEL_SJL/G_latest.pth"
    # elif rint == 1:
    #     config_dir = "D:/voice/VITStuning/OUTPUT_MODEL-M/config.json"
    #     model_dir = "D:/voice/VITStuning/OUTPUT_MODEL-M/G_latest.pth"
    # else:
    #     raise ValueError("No model found")

    global vits_net_g, vits_hps, vits_speaker_ids
    vits_hps = VITStuning.utils.get_hparams_from_file(config_path = config_dir)

    vits_net_g = SynthesizerTrn(
        len(vits_hps.symbols),
        vits_hps.data.filter_length // 2 + 1,
        vits_hps.train.segment_size // vits_hps.data.hop_length,
        n_speakers=vits_hps.data.n_speakers,
        **vits_hps.model).to(device)
    _ = vits_net_g.eval()

    _ = VITStuning.utils.load_checkpoint(model_dir, vits_net_g, None)
    vits_speaker_ids = vits_hps.speakers
    speakers = list(vits_hps.speakers.keys())
    speaker_id = vits_speaker_ids[roles[rint]]
    print("speakers: ", speakers, speaker_id)
    speed = speeds[rint]
    tts_fn = create_tts_fn(vits_net_g, vits_hps, speaker_id, speed)
    return tts_fn


def api_text_to_speech(text, speech_file_path):
    from openai import OpenAI
    client = OpenAI(
        api_key="sk-kcrdqzlwcmdygxnmflzptjnofxzdhquhjtfjagkdcqrnodof",  # 从 https://cloud.siliconflow.cn/account/ak 获取
        base_url="https://api.siliconflow.cn/v1"
    )
    """
    男生音色：

    沉稳男声: alex
    低沉男声: benjamin
    磁性男声: charles
    欢快男声: david
    女生音色：
    
    沉稳女声: anna
    激情女声: bella
    温柔女声: claire
    欢快女声: diana
    """
    with client.audio.speech.with_streaming_response.create(
            model="FunAudioLLM/CosyVoice2-0.5B",  # 支持 fishaudio / GPT-SoVITS / CosyVoice2-0.5B 系列模型
            voice="FunAudioLLM/CosyVoice2-0.5B:anna",  # 系统预置音色
            # 用户输入信息
            input=f"你能用高兴的情感说吗？<|endofprompt|>{text}",
            response_format="wav"  # 支持 mp3, wav, pcm, opus 格式
    ) as response:
        response.stream_to_file(speech_file_path)

def split_text_by_period(text, length=200):
    # 预处理文本：去除换行符和多余空格
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()

    # 使用正则表达式按句号分句（保留句号）
    sentences = re.split(r'(?<=。)', text)

    # 过滤空字符串并去除首尾空格
    sentences = [s.strip() for s in sentences if s.strip()]

    paragraphs = []
    current_paragraph = ''

    for sentence in sentences:
        # 如果当前段落加上新句子超过限制
        if len(current_paragraph) + len(sentence) > length:
            if current_paragraph:
                # 提交当前段落并开始新段落
                paragraphs.append(current_paragraph)
                current_paragraph = ''
            else:
                # 处理单个句子超过200字符的特殊情况
                paragraphs.append(sentence[:length])  # 强制截断
                current_paragraph = sentence[length:]
        else:
            current_paragraph += sentence

    # 添加最后一个段落
    if current_paragraph:
        paragraphs.append(current_paragraph)

    # 过滤可能存在的空段落
    return [p for p in paragraphs if p]

def speak_text(text,  language = "简体中文", role_id = 0, save_file = "file_trim_5s.wav", play_audio_flag = True, use_api = True):
    global tts_fn
    if not tts_fn:
        tts_fn = create_model(role_id = role_id)

    # 分割文本为200字左右的段落
    text_chunks = split_text_by_period(text)

    # 生成临时音频文件
    temp_files = []
    base_dir = os.path.join(os.path.dirname(__file__), "speaking_files")
    os.makedirs(base_dir, exist_ok=True)
    for idx, chunk in enumerate(text_chunks):
        chunk_path = os.path.join(base_dir, f"{format_folder_name(chunk)}.wav")
        print("speak_text:", chunk_path)
        # 根据需要设置输入参数的值
        # text, speaker, language, speed = "你好，世界！", "rosalia", '简体中文', 1.0
        if not use_api:
            fs_multi = 1.0
            if not os.path.exists(chunk_path):
                result, audio = tts_fn(chunk, language)
                if result == "Success":
                    write_audio(chunk_path, audio)
                else:
                    logger.info("生成语音失败: {}".format(result))
        else:
            fs_multi = 1.5
            if not os.path.exists(chunk_path):
                api_text_to_speech(chunk, chunk_path)
        temp_files.append(chunk_path)

    # 合并音频文件
    combined_audio = AudioSegment.empty()
    for tf in temp_files:
        combined_audio += AudioSegment.from_wav(tf)
    combined_audio.export(save_file, format="wav")

    # # 清理临时文件
    # for tf in temp_files:
    #     os.remove(tf)

    # 根据参数决定是否播放最终音频
    if play_audio_flag:
        play_audio(save_file, fs_multi=fs_multi)


if __name__=="__main__":
    base_dir = "D:\\story_pictures\\kehuanshijie\\precessed_txt"
    file_name = r"藏宝盒.txt"
    base_dir = "D:\\story_pictures\\1\\processed"
    file_name = r"飞行员.txt"
    content = "\n".join(open(os.path.join(base_dir, file_name), 'r', encoding='utf-8').readlines())
    speak_text(content, role_id = 0, save_file = file_name.replace(".txt", ".wav"), play_audio_flag = False)




