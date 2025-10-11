# -*- coding: utf-8 -*-
import streamlit as st
import os
import re
import requests
from urllib.parse import urlparse
from pathlib import Path
from ocr_model import SmartDocumentOCR, ArticleProcessor
from speaker_model import speak_text
from ai_tools import deepseek_revise
from tkinter import Tk, filedialog

# 定义一个函数来打开文件浏览器选择文件
def select_file():
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    root.attributes('-topmost', True)  # 确保文件对话框出现在最前面
    file_path = filedialog.askopenfilename()  # 打开文件选择对话框
    root.destroy()  # 关闭主窗口
    print("0选择的文件路径：{}".format(file_path))
    return file_path


def select_directory():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    dir_path = filedialog.askdirectory(
    )

    root.destroy()
    return dir_path



def text_2_audio(text_path, voice_type):
    """文本转语音处理函数"""
    base_dir = os.path.dirname(text_path)
    file_name = os.path.basename(text_path).split(".")[0]

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.readlines()
    content = "".join(text)

    # 使用AI优化文本
    revised_text = deepseek_revise(content)
    print("优化后的文本（部分）：", revised_text)
    if len(revised_text) > 1000:
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(revised_text)

    # 生成语音文件
    audio_path = os.path.join(base_dir, f"{file_name}.wav")
    speak_text(
        text=revised_text,
        language = "简体中文", role_id = voice_type,
        save_file=audio_path,
        play_audio_flag=True
    )
    return audio_path, revised_text


# 应用主界面
st.title("智能图文转换工具")

with st.container(border=True):
    # 语音合成模块
    voice_options = {
        "标准女声": 0,
        "标准男声": 1,
    }
    selected_voice = st.selectbox("选择声音", list(voice_options.keys()))
    if not "article_files" in st.session_state:
        st.session_state.article_files = []
    # 图片处理模块
    if st.button(":musical_note:请选择要转换为文本图片目录"):
        input_path = select_directory()
        st.session_state.article_files = []

        with st.spinner("正在处理中，请稍候..."):
            try:
                # 初始化处理模块
                output_path = "precessed_txt"
                output_dir = os.path.join(input_path, output_path)
                if not os.path.exists(output_dir):
                    print("开始从图片中提取文字！")
                    ocr = SmartDocumentOCR()
                    processor = ArticleProcessor(input_path, ocr, output_path=output_path)
                    st.session_state.article_files = processor.process_image_series()
                    st.session_state.output_dir = output_dir
                    print(st.session_state.article_files)
                else:
                    st.session_state.article_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(('.txt', '.md'))]
                    st.session_state.output_dir = output_dir
                st.success("文字转换完成！")
            except Exception as e:
                st.error(f"处理过程中发生错误：{str(e)}")

with st.container(border=True):
    if st.session_state.get("article_files", []):
        try:
            # 显示结果文件
            output_files = [f for f in os.listdir(st.session_state.output_dir) if f.endswith(('.txt', '.md'))]
            if output_files:
                st.subheader("生成内容管理")
                col1, col2 = st.columns([2, 3])

                with col1:
                    selected_file = st.selectbox(
                        "选择要转换的文本文件",
                        output_files,
                        index=0
                    )

                    text_path = os.path.join(st.session_state.output_dir, selected_file)

                    with open(text_path, "r", encoding="utf-8") as f:
                        text_content = f.read(500) + "..."
                    st.text_area("文本预览", text_content, height=200)

                with col2:
                    if st.button("生成语音"):
                        with st.spinner("正在生成语音..."):
                            try:
                                audio_path, revised_text = text_2_audio(
                                    text_path,
                                    voice_type=voice_options[selected_voice],
                                )

                                st.write("优化后的文本（部分）：")
                                st.write(revised_text[:500] + "...")
                                st.audio(audio_path, format='audio/wav')

                                with open(audio_path, "rb") as f:
                                    st.download_button(
                                        label="下载语音文件",
                                        data=f,
                                        file_name=os.path.basename(audio_path),
                                        mime="audio/wav"
                                    )

                            except Exception as e:
                                st.error(f"语音生成失败: {str(e)}")

                # 原始文件下载
                st.subheader("生成文件列表")
                for file in output_files:
                    file_path = os.path.join(st.session_state.output_dir, file)
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"下载 {file}",
                            data=f,
                            file_name=file
                        )
            else:
                st.warning("未找到生成的文件")
        except Exception as e:
            st.error(f"处理过程中发生错误：{str(e)}")

    # 侧边栏说明
    st.sidebar.markdown("""
    ### 使用说明
    1. 点击「请选择要转换为文本图片目录」按钮
    2. 选择生成的文本文件进行语音转换
    3. 下载生成的音频文件

    功能特性：
    - 自动OCR文字识别
    - 文本AI优化
    - 语音合成输出
    - 多格式文件下载
    """)

