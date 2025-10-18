import os
import time
from pathlib import Path
from tkinter import Tk, filedialog

import streamlit as st
from natsort import natsorted

from logger import logger
from models.workflow import AssetConfig, ServiceConfig, StepConfig, WorkflowConfig
from orchestrator import Orchestrator
from services.registry import ServiceRegistry


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

if "start_file_name" not in st.session_state:
    st.session_state.start_file_name = None


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
            st.session_state["transcripts"] = []

            split_cfg = WorkflowConfig(
                id="split_selected_audio",
                title="Split Selected Audio",
                services=[
                    ServiceConfig(
                        name="splitter",
                        impl="services.defaults.create_splitter",
                        options={
                            "min_silence_len": 500,
                            "silence_thresh": 16
                        },
                    ),
                    ServiceConfig(
                        name="stt",
                        impl="services.defaults.create_stt",
                        options={"model_size": "tiny", "device": "cpu"},
                    )
                ],
                steps=[
                    StepConfig(id="split", type="split", service="splitter"),
                    StepConfig(
                        id="transcribe",
                        type="transcribe",
                        service="stt",
                        params={"force_transcribe": True},
                    ),
                ],
                assets=[AssetConfig(id="selected_audio", source_uri=tmp_audio_path)],
            )

            registry = ServiceRegistry()
            orchestrator = Orchestrator(split_cfg, registry)
            ctx = orchestrator.run_asset(split_cfg.assets[0])
            artifacts = ctx.get("artifacts", {})
            split_info = artifacts.get("split", {})
            target_dir = split_info.get("target_dir")
            chunk_paths = artifacts.get("chunks", [])
            transcripts = artifacts.get("transcripts", [])

            if target_dir:
                st.session_state.target_dir = target_dir
            if chunk_paths:
                chunk_names = [Path(p).name for p in chunk_paths if Path(p).name]
                st.session_state.files = natsorted(chunk_names)
            else:
                st.session_state.files = []
            if transcripts:
                st.session_state.transcripts = transcripts
        else:
            st.error("未选择文件")

    audio_path = st.session_state.get("selected_file_path", None)
    if audio_path:
        # 1. 使用 st.success 提示用户文件已选择
        st.success(f"已选择的文件路径：{audio_path}")

    if "files" not in st.session_state:
        st.session_state.files = []

    if st.session_state.files:
        start_file_name = st.selectbox(
            "选择起始播放的文件",
            options=st.session_state.files,
            key="file_idx",
        )
        st.session_state.start_file_name = start_file_name
    else:
        st.info("请先选择音频文件完成切分。")
        st.session_state.start_file_name = None
    if st.session_state.get("transcripts"):
        with st.expander("识别文本（实验功能）", expanded=False):
            for item in st.session_state.transcripts:
                st.write(f"- `{Path(item['file']).name}`: {item['text']}")


#################################################


with st.container(border=True):
    run_button = st.button(":arrow_forward: 点击开始播放", key="run_button")
    pause_button = st.button(":black_square_for_stop: 点击暂停播放", key="pause_button")

    if pause_button:
        st.session_state.paused = True
        st.markdown(f"#### 	:smiley: 播放暂停!")

    if run_button:
        if st.session_state.get("target_dir") is None or not st.session_state.files:
            st.error("请先选择一个文件")
        elif integer_value is None:
            st.error("请选择一个整数")
        else:
            # 输入有效，执行函数
            st.markdown(f"#### :musical_note: 开始播放...")
            logger_place_holder = st.empty()

            translate_flag = st.session_state.get("translate_chinese", translate_chinese)

            playback_cfg = WorkflowConfig(
                id="playback_selected_audio",
                title="Playback Selected Audio",
                services=[
                    ServiceConfig(
                        name="splitter",
                        impl="services.defaults.create_splitter",
                        options={
                            "min_silence_len": 500,
                            "silence_thresh": 16,
                            "model_size": "tiny",
                            "device": "cpu",
                        },
                    ),
                    ServiceConfig(
                        name="playback",
                        impl="services.defaults.create_playback",
                        options={"initial_repeats": 1, "initial_threshold": 3},
                    ),
                    ServiceConfig(
                        name="stt",
                        impl="services.defaults.create_stt",
                        options={"model_size": "tiny", "device": "cpu"},
                    ),
                ],
                steps=[
                    StepConfig(id="split", type="split", service="splitter"),
                    StepConfig(
                        id="transcribe",
                        type="transcribe",
                        service="stt",
                        params={"force_transcribe": False},
                    ),
                    StepConfig(
                        id="play",
                        type="speak",
                        service="playback",
                        params={
                            "repeats": integer_value,
                            "translate": translate_flag == "是",
                            "start_file": st.session_state.get("start_file_name"),
                        },
                    ),
                ],
                assets=[
                    AssetConfig(
                        id="selected_audio",
                        source_uri=st.session_state["selected_file_path"],
                    )
                ],
            )

            registry = ServiceRegistry()
            orchestrator = Orchestrator(playback_cfg, registry)

            def on_progress(file_name: str, idx: int) -> None:
                logger_place_holder.text(
                    f"🚀 {time.strftime('%Y-%m-%d %H:%M:%S')} - {file_name}"
                )
                st.session_state.playing_file_idx = idx

            ctx = orchestrator.run_asset(
                playback_cfg.assets[0],
                extra_context={"callbacks": {"on_progress": on_progress}},
            )

            artifacts = ctx.get("artifacts", {})
            playback_info = artifacts.get("playback", {})
            transcripts = artifacts.get("transcripts")
            if transcripts:
                st.session_state.transcripts = transcripts
            if playback_info.get("last_played"):
                st.session_state.finished = True
                st.markdown("#### 	:smiley: 播放结束! 可选择重听的序号:")
            else:
                st.session_state.finished = False


#################################################


with st.sidebar:
    st.markdown("### 配置化工作流（实验功能）")
    config_path = st.text_input("配置文件路径", value="")
    run_config = st.button("运行配置工作流", disabled=not config_path)
    if run_config:
        try:
            cfg = WorkflowConfig.model_validate_json(Path(config_path).read_text(encoding="utf-8"))
            registry = ServiceRegistry()
            orchestrator = Orchestrator(cfg, registry)
            results = list(orchestrator.run_all())
            st.success(f"成功执行 {len(results)} 个任务。")
            if results:
                last = results[-1]
                artifacts = last.get("artifacts", {})
                st.json(artifacts)
        except FileNotFoundError:
            st.error("未找到配置文件，请检查路径。")
        except Exception as exc:  # pylint: disable=broad-except
            st.error(f"执行失败：{exc}")
