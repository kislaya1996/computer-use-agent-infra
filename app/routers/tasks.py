from fastapi import APIRouter, Depends

from app.dependencies import verify_api_key
from app.schemas.task import TaskRequest, TaskResponse
from app.services import task_service

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.post("/", response_model=TaskResponse, status_code=202)
def create_task(
    task: TaskRequest,
    user_id: str = Depends(verify_api_key),
) -> TaskResponse:
    return task_service.enqueue_task(task, user_id)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    user_id: str = Depends(verify_api_key),
) -> TaskResponse:
    return task_service.get_task(task_id)
