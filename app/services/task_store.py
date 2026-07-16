import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.schemas.task import TaskResponse

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"


class TaskStore:
    def __init__(self, root: Path = RUNS_DIR) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: Dict[str, threading.Lock] = {}
        self._global = threading.Lock()

    def _lock(self, task_id: str) -> threading.Lock:
        with self._global:
            if task_id not in self._locks:
                self._locks[task_id] = threading.Lock()
            return self._locks[task_id]

    def task_dir(self, task_id: str) -> Path:
        path = self.root / task_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def meta_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "meta.json"

    def create(
        self,
        task_id: str,
        name: str,
        payload: str,
        user_id: str,
        priority: str,
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat() + "Z"
        meta: Dict[str, Any] = {
            "task_id": task_id,
            "name": name,
            "payload": payload,
            "user_id": user_id,
            "priority": priority,
            "status": "queued",
            "result": "",
            "container_id": None,
            "exit_code": None,
            "log_path": None,
            "attempts": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        self.save(meta)
        return meta

    def save(self, meta: Dict[str, Any]) -> None:
        task_id = meta["task_id"]
        meta["updated_at"] = datetime.utcnow().isoformat() + "Z"
        with self._lock(task_id):
            self.meta_path(task_id).write_text(
                json.dumps(meta, indent=2),
                encoding="utf-8",
            )

    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        path = self.meta_path(task_id)
        if not path.exists():
            return None
        with self._lock(task_id):
            return json.loads(path.read_text(encoding="utf-8"))

    def update(self, task_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        meta = self.load(task_id)
        if meta is None:
            return None
        meta.update(fields)
        self.save(meta)
        return meta

    def to_response(self, meta: Dict[str, Any]) -> TaskResponse:
        return TaskResponse(
            task_id=meta["task_id"],
            name=meta["name"],
            status=meta["status"],
            result=meta.get("result") or "",
            user_id=meta.get("user_id"),
            priority=meta.get("priority"),
            container_id=meta.get("container_id"),
            exit_code=meta.get("exit_code"),
            log_path=meta.get("log_path"),
            attempts=meta.get("attempts"),
            error=meta.get("error"),
        )


task_store = TaskStore()
