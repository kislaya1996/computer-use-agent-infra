import subprocess
import sys
import uuid
from pathlib import Path

from app.schemas.task import TaskRequest, TaskResponse

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "placeholder_task.py"


def run_task(task: TaskRequest) -> TaskResponse:
    task_id = str(uuid.uuid4())
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), task.name, task.payload],
        capture_output=True,
        text=True,
        check=False,
    )
    status = "completed" if completed.returncode == 0 else "failed"
    result = completed.stdout.strip() if completed.returncode == 0 else completed.stderr.strip()
    return TaskResponse(task_id=task_id, name=task.name, status=status, result=result)
