import time
import uuid
from pathlib import Path

import docker
from docker import DockerClient
from fastapi import HTTPException

from app.queue.priority_queue import priority_queue
from app.queue.rate_limit import rate_limiter
from app.schemas.task import TaskRequest, TaskResponse
from app.services.task_store import task_store

WORKER_IMAGE = "cua-worker:local"
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
READY_TIMEOUT_SECONDS = 30
READY_POLL_INTERVAL_SECONDS = 0.5


def enqueue_task(task: TaskRequest, user_id: str) -> TaskResponse:
    allowed, reason = rate_limiter.check_submit(user_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    task_id = str(uuid.uuid4())
    meta = task_store.create(
        task_id=task_id,
        name=task.name,
        payload=task.payload,
        user_id=user_id,
        priority=task.priority,
    )
    rate_limiter.mark_queued(user_id)
    priority_queue.enqueue(
        {
            "task_id": task_id,
            "name": task.name,
            "payload": task.payload,
            "user_id": user_id,
            "priority": task.priority,
        }
    )
    return task_store.to_response(meta)


def get_task(task_id: str) -> TaskResponse:
    meta = task_store.load(task_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_store.to_response(meta)


def execute_task(task_id: str) -> None:
    meta = task_store.load(task_id)
    if meta is None:
        return

    user_id = meta["user_id"]
    task = TaskRequest(
        name=meta["name"],
        payload=meta.get("payload") or "",
        priority=meta.get("priority") or "normal",
    )
    run_dir = task_store.task_dir(task_id)
    rate_limiter.mark_running(user_id)
    task_store.update(task_id, status="running")

    client = docker.from_env()
    container = None
    exit_code = 1
    attempt = 0
    try:
        container = client.containers.run(
            WORKER_IMAGE,
            environment={
                "TASK_ID": task_id,
                "TASK_NAME": task.name,
                "TASK_PAYLOAD": task.payload,
            },
            detach=True,
        )
        task_store.update(task_id, container_id=container.id, log_path=str(run_dir))
        _wait_until_ready(client, container)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            log_path = run_dir / f"attempt_{attempt}.log"
            exit_code = _exec_task(client, container.id, task, log_path, attempt)
            if exit_code == 0:
                break
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS)

        status = "completed" if exit_code == 0 else "failed"
        task_store.update(
            task_id,
            status=status,
            result=f"exit_code={exit_code} after {attempt} attempts",
            exit_code=exit_code,
            attempts=attempt,
            log_path=str(run_dir),
            container_id=container.id if container else None,
        )
    except Exception as exc:
        task_store.update(
            task_id,
            status="failed",
            error=str(exc),
            result=str(exc),
            attempts=attempt or None,
            log_path=str(run_dir),
            container_id=container.id if container else None,
        )
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass
        rate_limiter.mark_finished(user_id)


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
