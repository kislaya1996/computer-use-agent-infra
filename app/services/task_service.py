import time
import uuid
from datetime import datetime
from pathlib import Path

import docker
from docker import DockerClient

from app.schemas.task import TaskRequest, TaskResponse

WORKER_IMAGE = "cua-worker:local"
RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2


def run_task(task: TaskRequest) -> TaskResponse:
    task_id = str(uuid.uuid4())
    client = docker.from_env()

    container = client.containers.run(
        WORKER_IMAGE,
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

    exit_code = 1
    attempt = 0
    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            log_path = run_dir / f"attempt_{attempt}.log"
            exit_code = _exec_task(client, container.id, task, log_path, attempt)
            if exit_code == 0:
                break
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS)
    finally:
        container.remove(force=True)

    return TaskResponse(
        task_id=task_id,
        name=task.name,
        status="completed" if exit_code == 0 else "failed",
        result=f"exit_code={exit_code} after {attempt} attempt(s)",
        container_id=container.id,
        exit_code=exit_code,
        log_path=str(run_dir),
        attempts=attempt,
    )


def _exec_task(
    client: DockerClient,
    container_id: str,
    task: TaskRequest,
    log_path: Path,
    attempt: int,
) -> int:
    api = client.api
    exec_id = api.exec_create(
        container_id,
        cmd=["python", "-u", "/app/run_task.py", task.name, task.payload],
    )["Id"]
    stream = api.exec_start(exec_id, stream=True)

    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(f"=== attempt {attempt} ===\n")
        log_file.flush()
        for chunk in stream:
            log_file.write(chunk.decode("utf-8", errors="replace"))
            log_file.flush()

    code = api.exec_inspect(exec_id).get("ExitCode")
    return code if isinstance(code, int) else 1
