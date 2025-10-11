import streamlit as st
from logger import logger
import time
import os
from audio_process_and_replay import main_split_and_replay_audio, split_audio, replay_single_audio
from tkinter import Tk, filedialog
from natsort import natsorted


tmp_audio_path = None
# 直到用户正确输入信息为止
st.markdown(f"# 英文自动听读")


# 定义一个函数来打开文件浏览器选择文件
def select_file():
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    root.attributes('-topmost', True)  # 确保文件对话框出现在最前面
    file_path = filedialog.askopenfilename()  # 打开文件选择对话框
    root.destroy()  # 关闭主窗口
    logger.info("0选择的文件路径：{}".format(file_path))
    return file_path

#################################################
# 初始化暂停状态
if 'paused' not in st.session_state:
    st.session_state.paused = False

if "playing_file_idx" not in st.session_state:
  st.session_state.playing_file_idx = None

if "finished" not in st.session_state:
  st.session_state.finished = None


with st.container(border=True):
    # streamlit 设置多列，比例为0.3， 0.3， 0.4
    col1, col2 = st.columns([0.5, 0.5])

    with col1:
        # 整数选择框，范围1到10
        integer_value = st.slider(":1234: **请选择句子重复播放的次数（1-4）**", min_value=1, max_value=4, value = 2, key="integer_value")
    with col2:
        # 增加radio按钮，是否翻译成中文
        translate_chinese = st.radio(":rainbow-flag: **是否朗读中文翻译**", index=1,options=["是", "否"], key="translate_chinese")

    # 文件选择框
    if st.button(":musical_note:请选择要播放的音频"):
        tmp_audio_path = select_file()
        if tmp_audio_path:  # 如果用户选择了文件
            st.session_state["selected_file_path"] = tmp_audio_path
            st.session_state["playing_file_idx"] = None
            st.session_state["finished"] = False
            target_dir = os.path.join(os.path.dirname(tmp_audio_path), tmp_audio_path.split(".")[0])
            os.makedirs(target_dir, exist_ok=True)
            split_audio(tmp_audio_path, target_dir)
            st.session_state.target_dir = target_dir
            st.session_state.files = natsorted(os.listdir(target_dir))
            # 切分音频文件
        else:
            st.error("未选择文件")

    audio_path = st.session_state.get("selected_file_path", None)
    if audio_path:
        # 1. 使用 st.success 提示用户文件已选择
        st.success(f"已选择的文件路径：{audio_path}")

    if not "files" in st.session_state:
        st.session_state.files = ["未选择文件", "未选择文件"]
    print(st.session_state.files)
    start_file_idx = st.selectbox("选择起始播放的文件", options=st.session_state.files, index = 1, key="file_idx")
    st.session_state.playing_file_idx = st.session_state.files.index(start_file_idx)


#################################################


with st.container(border=True):
    run_button = st.button(":arrow_forward: 点击开始播放", key="run_button")
    pause_button = st.button(":black_square_for_stop: 点击暂停播放", key="pause_button")

    if pause_button:
        st.session_state.paused = True
        st.markdown(f"#### 	:smiley: 播放暂停!")

    if run_button:
        if st.session_state.target_dir is None or not "files" in st.session_state:
            st.error("请先选择一个文件")
        elif integer_value is None:
            st.error("请选择一个整数")
        else:
            # 输入有效，执行函数
            st.markdown(f"#### :musical_note: 开始播放...")
            logger_place_holder = st.empty()
            for fidx, file_name in enumerate(st.session_state.files):
                if fidx == 0:
                    continue
                if fidx < 3:
                    repeats = 1
                else:
                    repeats = integer_value
                if st.session_state.paused:
                    # 暂停时当前播放的idx需要加一
                    st.session_state.paused = False
                    # st.session_state.playing_file_idx = fidx+1
                fidx = int(file_name.split("_")[0][1:])
                if st.session_state.playing_file_idx and st.session_state.playing_file_idx > fidx:
                    logger.info("跳过播放: {}".format(file_name))
                    continue
                elif st.session_state.playing_file_idx and st.session_state.playing_file_idx == fidx:
                    # 播放一次上次暂停的音频
                    replay_single_audio(os.path.join(st.session_state.target_dir, file_name), 1)
                    continue
                logger_place_holder.text(f"🚀 {time.strftime('%Y-%m-%d %H:%M:%S')} - {file_name}")
                # 重复播放音频
                replay_single_audio(os.path.join(st.session_state.target_dir, file_name), repeats)
                st.session_state.playing_file_idx = fidx
                if fidx == len(st.session_state.files) - 1:
                    st.session_state.finished = True
            if st.session_state.finished:
                st.markdown(f"#### 	:smiley: 播放结束! 可选择重听的序号:")

