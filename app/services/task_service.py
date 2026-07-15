import uuid
from datetime import datetime
from pathlib import Path

import docker

from app.schemas.task import TaskRequest, TaskResponse

WORKER_IMAGE = "cua-worker:local"
RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"


def run_task(task: TaskRequest) -> TaskResponse:
    task_id = str(uuid.uuid4())
    client = docker.from_env()
    container = client.containers.run(
        WORKER_IMAGE,
        command=["python", "-u", "/app/run_task.py", task.name, task.payload],
        environment={
            "TASK_ID": task_id,
            "TASK_NAME": task.name,
            "TASK_PAYLOAD": task.payload,
        },
        detach=True,
    )

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS_DIR / f"{container.id[:12]}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "worker.log"

    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            for chunk in container.logs(stream=True, follow=True):
                log_file.write(chunk.decode("utf-8", errors="replace"))
                log_file.flush()
        exit_code = int(container.wait().get("StatusCode", 1))
    finally:
        container.remove(force=True)
        # could add remove as a parameter to run, but then 
        # container.logs cannot be streamed. It ends up in a race condition where 
        # logs to be written and remove compete. This gives a lot more control.
        # We can further break down container.run into container.create->container.start->logic->container.remove

    return TaskResponse(
        task_id=task_id,
        name=task.name,
        status="completed" if exit_code == 0 else "failed",
        result=str(log_path),
        container_id=container.id,
        exit_code=exit_code,
        log_path=str(log_path),
    )
