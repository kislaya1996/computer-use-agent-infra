from typing import Optional

from pydantic import BaseModel


class TaskRequest(BaseModel):
    name: str
    payload: str = ""


class TaskResponse(BaseModel):
    task_id: str
    name: str
    status: str
    result: str
    container_id: Optional[str] = None
    exit_code: Optional[int] = None
    log_path: Optional[str] = None
    attempts: Optional[int] = None
