import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workflow_runner import load_workflow, run_workflow

wf = load_workflow("config/workflows/history_science_english.json")
run_workflow(
    wf,
    progress_path="config/workflows/history_science_english.json",  # 写回同一配置
)
