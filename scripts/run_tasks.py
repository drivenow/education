import sys
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workflow_runner import load_workflow, run_workflow

config_file = sys.argv[1]
wf = load_workflow(config_file)
run_workflow(
    wf,
    progress_path=config_file,  # 写回同一配置
)
