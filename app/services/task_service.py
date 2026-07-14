import uuid

import docker

from app.schemas.task import TaskRequest, TaskResponse

WORKER_IMAGE = "cua-worker:local"


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
        remove=True,
    )
    return TaskResponse(
        task_id=task_id,
        name=task.name,
        status="started",
        result=container.id,
    )
