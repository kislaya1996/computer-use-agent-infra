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
READY_TIMEOUT_SECONDS = 30
READY_POLL_INTERVAL_SECONDS = 0.5


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
        _wait_until_ready(client, container)
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


def _wait_until_ready(client: DockerClient, container) -> None:
    api = client.api
    probe = ["python", "/app/healthcheck.py"]
    deadline = time.time() + READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        container.reload()
        if container.status == "exited":
            raise RuntimeError("worker container exited before becoming ready")
        exec_id = api.exec_create(container.id, probe)["Id"]
        api.exec_start(exec_id)
        if api.exec_inspect(exec_id).get("ExitCode") == 0:
            return
        time.sleep(READY_POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"worker not ready within {READY_TIMEOUT_SECONDS}s")


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
