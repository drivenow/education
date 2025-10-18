## 项目概述

本仓库实现了一套面向儿童英语听读教育的工作流平台。核心目标是把传统的“切分音频 → 识别 → 翻译 → 复读”流程抽象成统一的服务和工作流配置，以便快速扩展新的教材或学习任务。

### 主要功能
- **可视化应用**：`App.py` 提供 Streamlit 前端，支持选择音频、配置重复次数和翻译选项，面向家长或教师。
- **OCR 转语音工具**：`App_ocr.py` 通过 OCR 识别图片、使用 LLM 优化文本并生成语音，适合图文教材。
- **工作流框架**：
  - `models/workflow.py` 定义 `WorkflowConfig`、`ServiceConfig`、`StepConfig` 等核心模型。
  - `services/` 目录包含默认服务实现：音频切分、Whisper 识别、翻译、VITS/外部 TTS 等。
  - `orchestrator.py` 根据配置驱动步骤执行，支持按素材覆写部分参数。
- **命令行工具**：`workflow_runner.py` 支持从配置或单文件运行工作流，覆盖切分、识别、播报的完整流程。
- **周计划示例**：`config/workflows/weekly_listening.json` 复刻 legacy 模块的每周听读安排，可按日期执行。
- **保留旧逻辑**：`legacy/` 存放原 `audio_process_and_replay.py` 及迁移后的批处理入口以便参考。

---

## 快速开始

### 1. 环境准备
仓库使用 `pyproject.toml` + `uv` 管理依赖，默认包含 Whisper、pydub、sounddevice、Streamlit 等。

```bash
uv sync    # 安装依赖
uv run python -m streamlit run App.py   # 运行听读前端
```

必要的外部要求：
- **FFmpeg**：pydub 读取 MP3/M4A 所需。
- **SoundDevice**：播放音频需要可用声卡。
- **Whisper**：默认使用 `small` 模型，且尝试在 GPU（CUDA）上运行，可在参数中改为 `cpu`。
- **外部翻译/TTS**：`translate_model.py`、`speaker_model.py` 依赖本地 Ollama、VITS 模型等，请提前配置。

### 2. 运行 Streamlit 应用
```bash
uv run streamlit run App.py
uv run streamlit run App_ocr.py
```
`App.py` 提供可视化听读；`App_ocr.py` 支持图文 → 语音转换。

### 3. 命令行方式运行工作流

#### 3.1 针对单个音频
```bash
uv run python workflow_runner.py \
  --audio /path/to/audio.mp3 \
  --repeats 2 \
  --model-size small \
  --device cuda
```
- `--no-translate`：关闭中文翻译；`--no-playback`：跳过播放，适合无声卡环境。

#### 3.2 使用配置文件
`config/workflows/weekly_listening.json` 复刻旧版周计划。示例：
```bash
uv run python workflow_runner.py \
  --config config/workflows/weekly_listening.json \
  --day Mon        # 仅执行周一计划
  --no-playback    # 只切分+识别
```
- `--asset-id` 可以指定具体教材。
- 配置中使用的音频路径需替换为你本地真实存在的文件。

### 4. Legacy 模块
旧版流程保存在 `legacy/`：
- `legacy/audio_process_and_replay.py`：原脚本，仅供参考。
- `legacy/main_audio_workflow.py`：将旧逻辑映射到工作流的命令行入口。
```bash
python legacy/main_audio_workflow.py --day Mon
```

---

## 工作流配置说明

工作流配置由 `models/workflow.py` 定义的四个模型组成：

| 模型             | 说明                                                         |
|------------------|--------------------------------------------------------------|
| `ServiceConfig`  | 声明运行时需要的服务实例，包含 `name`、`impl`、`options`    |
| `StepConfig`     | 定义步骤的执行顺序与参数：`id`、`type`、`service`、`params` |
| `AssetConfig`    | 需要处理的素材（基于 `TaskMeta`），支持 `lang`、`crontab`、`steps` 等参数 |
| `WorkflowConfig` | 顶层入口，包含 `services`、`steps`、`assets`                 |

示例（节选自 `config/workflows/grade1_example.json`）：

```json
{
  "services": [
    {"name": "splitter", "impl": "services.defaults.create_splitter"},
    {"name": "stt", "impl": "services.defaults.create_stt"},
    {"name": "translator", "impl": "services.defaults.create_translator"},
    {"name": "tts", "impl": "services.defaults.create_playback"}
  ],
  "steps": [
    {"id": "split", "type": "split", "service": "splitter"},
    {"id": "transcribe", "type": "transcribe", "service": "stt"},
    {"id": "translate", "type": "translate", "service": "translator"},
    {"id": "play", "type": "speak", "service": "tts", "params": {"repeats": 2}}
  ],
  "assets": [
    {"id": "lesson1", "source_uri": "/path/to/audio_lesson_1.mp3"}
  ]
}
```

### `steps` 覆写
若某个素材需要微调参数，可在 `AssetConfig.steps` 中直接设置覆盖值。例如：

```json
{
  "steps": {
    "play": { "repeats": 1, "translate": true }
  },
  "lang": "en",
  "crontab": "Mon",
  "max_session_seconds": 900
}
```

表示在 `play` 步骤使用重复 1 次、开启翻译，其余步骤仍按全局配置执行。`max_session_seconds` 用于限制单次播放的最长时长（若语言为英文，实际时长会除以 3），超过后本次 session 自动停止。覆写只允许修改现有步骤的参数或 service 名，不能增加/删除步骤，以保持流程结构一致。

### 常见配置文件
- `config/workflows/split_transcribe_example.json`：最小示例，仅演示切分与识别。
- `config/workflows/weekly_listening.json`：完整周计划，与旧版脚本等价，可配合 `workflow_runner.py --day Mon` 等过滤运行。
- `legacy/main_audio_workflow.py`：使用代码构造上述配置并执行，供迁移对照。

### StepContext 说明
服务执行时都会收到一个 `StepContext` 实例，主要包含：

- `workflow`：当前的 `WorkflowConfig`。
- `asset`：正在处理的素材（继承自 `TaskMeta`，含播放进度、`max_session_seconds` 等信息）。
- `step`：此次执行对应的 `StepConfig`。
- `settings`：已经合并好的参数字典（全局默认 + 资产覆写 + 运行时覆写），服务逻辑只需读取这一份。
- `artifacts`：跨步骤共享的可变存储，用于传递切分结果、识别文本、播放进度等。
- `extras`：可选附加上下文，例如 `callbacks`、临时覆写等。

建议服务实现只通过 `context.settings` 读取参数，并将中间产物写入 `context.artifacts`，从而保持流程统一清晰。

---

## 目录结构
```
.
├── App.py                        # Streamlit 听读前端
├── App_ocr.py                    # 图文转语音工具
├── config/
│   └── workflows/
│       ├── split_transcribe_example.json
│       ├── grade1_example.json
│       └── weekly_listening.json   # 周计划示例
├── models/
│   └── workflow.py               # Workflow/Data 模型定义
├── orchestrator.py               # 工作流调度核心
├── services/
│   ├── defaults.py               # 默认服务实现：切分/识别/播放/TTS
│   ├── base.py                   # StepContext & BaseService 接口
│   └── registry.py               # 服务注册/工厂
├── workflow_runner.py            # CLI 运行工作流
├── legacy/
│   ├── audio_process_and_replay.py
│   └── main_audio_workflow.py
├── speech2text_model.py          # Whisper 封装
├── translate_model.py            # 翻译调用（依赖本地 Ollama 服务）
├── speaker_model.py              # 自定义 TTS（依赖 VITStuning）
├── audio_utils.py                # 播放/重采样工具
├── pyproject.toml                # 项目依赖
└── README.md
```

---

## 常见问题
- **音频路径不存在**：请修改配置文件或命令行参数，使其指向本地真实文件。
- **Whisper 加载慢/报错**：首次运行需要下载模型，网络环境不佳时会超时；可预先下载或者改用 `tiny` 模型。
- **无法播放音频**：`sounddevice` 需可用声卡；在服务器上运行时可以加 `--no-playback`。
- **翻译/语音合成失败**：确认 `translate_model.py` 指定的服务（如 Ollama）处于可访问状态；`speaker_model.py` 依赖 VITStuning 及相关权重。
- **复用旧逻辑**：可直接运行 `legacy/main_audio_workflow.py`，或参考 `weekly_listening.json` 调整新的流程。

---

## 下一步规划
- 将 OCR 场景纳入统一工作流管理。
- 为工作流添加更多评测/测验步骤。
- 引入 CI/测试用例，确保核心服务修改后行为稳定。
