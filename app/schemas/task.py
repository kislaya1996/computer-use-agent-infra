from pydantic import BaseModel


class TaskRequest(BaseModel):
    name: str
    payload: str = ""


class TaskResponse(BaseModel):
    task_id: str
    name: str
    status: str
    result: str
