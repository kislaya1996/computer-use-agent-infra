from fastapi import APIRouter, Depends

from app.dependencies import verify_api_key
from app.schemas.task import TaskRequest, TaskResponse
from app.services import task_service

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/", response_model=TaskResponse)
def create_task(task: TaskRequest) -> TaskResponse:
    return task_service.run_task(task)
