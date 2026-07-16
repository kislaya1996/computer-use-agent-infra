import json
import os
from typing import Any, Dict, Optional

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
QUEUE_KEYS = {
    "high": "queue:high",
    "normal": "queue:normal",
    "low": "queue:low",
}
PRIORITY_ORDER = ("high", "normal", "low")


class PriorityQueue:
    def __init__(self, url: str = REDIS_URL) -> None:
        self.client = redis.Redis.from_url(url, decode_responses=True)

    def ping(self) -> bool:
        return bool(self.client.ping())

    def enqueue(self, job: Dict[str, Any]) -> None:
        priority = job.get("priority", "normal")
        if priority not in QUEUE_KEYS:
            priority = "normal"
        self.client.rpush(QUEUE_KEYS[priority], json.dumps(job))

    def dequeue(self, timeout: int = 2) -> Optional[Dict[str, Any]]:
        keys = [QUEUE_KEYS[p] for p in PRIORITY_ORDER]
        result = self.client.blpop(keys, timeout=timeout)
        if result is None:
            return None
        _key, payload = result
        return json.loads(payload)

    def depth(self, priority: Optional[str] = None) -> int:
        if priority is not None:
            return int(self.client.llen(QUEUE_KEYS[priority]))
        return sum(int(self.client.llen(QUEUE_KEYS[p])) for p in PRIORITY_ORDER)


priority_queue = PriorityQueue()
