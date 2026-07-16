import os
from typing import Tuple

import redis

from app.queue.priority_queue import REDIS_URL

RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10"))
MAX_QUEUE_DEPTH_PER_USER = int(os.environ.get("MAX_QUEUE_DEPTH_PER_USER", "20"))
MAX_PER_USER_RUNNING = int(os.environ.get("MAX_PER_USER_RUNNING", "2"))


class RateLimiter:
    def __init__(self, url: str = REDIS_URL) -> None:
        self.client = redis.Redis.from_url(url, decode_responses=True)

    def check_submit(self, user_id: str) -> Tuple[bool, str]:
        rate_key = f"rate:{user_id}"
        count = self.client.incr(rate_key)
        if count == 1:
            self.client.expire(rate_key, 60)
        if count > RATE_LIMIT_PER_MINUTE:
            return False, f"rate limit exceeded ({RATE_LIMIT_PER_MINUTE}/min)"

        queued = int(self.client.get(f"queued:{user_id}") or 0)
        if queued >= MAX_QUEUE_DEPTH_PER_USER:
            return False, f"queue depth limit exceeded ({MAX_QUEUE_DEPTH_PER_USER})"

        return True, ""

    def mark_queued(self, user_id: str) -> None:
        self.client.incr(f"queued:{user_id}")

    def mark_dequeued(self, user_id: str) -> None:
        key = f"queued:{user_id}"
        value = self.client.decr(key)
        if value < 0:
            self.client.set(key, 0)

    def mark_running(self, user_id: str) -> None:
        self.mark_dequeued(user_id)
        self.client.incr(f"running:{user_id}")

    def mark_finished(self, user_id: str) -> None:
        key = f"running:{user_id}"
        value = self.client.decr(key)
        if value < 0:
            self.client.set(key, 0)

    def can_run(self, user_id: str) -> bool:
        running = int(self.client.get(f"running:{user_id}") or 0)
        return running < MAX_PER_USER_RUNNING


rate_limiter = RateLimiter()
