from typing import Literal, Optional

from pydantic import BaseModel


class TaskRequest(BaseModel):
    name: str
    payload: str = ""
    priority: Literal["high", "normal", "low"] = "normal"


class TaskResponse(BaseModel):
    task_id: str
    name: str
    status: str
    result: str = ""
    user_id: Optional[str] = None
    priority: Optional[str] = None
    container_id: Optional[str] = None
    exit_code: Optional[int] = None
    log_path: Optional[str] = None
    attempts: Optional[int] = None
    error: Optional[str] = None
