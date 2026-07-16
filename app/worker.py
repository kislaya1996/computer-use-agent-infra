import logging
import os
import threading
import time
from typing import Optional

from app.queue.priority_queue import priority_queue
from app.queue.rate_limit import rate_limiter
from app.services import task_service

logger = logging.getLogger(__name__)

MAX_GLOBAL_RUNNING = int(os.environ.get("MAX_GLOBAL_RUNNING", "3"))
_semaphore = threading.Semaphore(MAX_GLOBAL_RUNNING)
_stop_event: Optional[threading.Event] = None
_thread: Optional[threading.Thread] = None


def start() -> None:
    global _stop_event, _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop_event = threading.Event()
    _thread = threading.Thread(target=_loop, name="task-worker", daemon=True)
    _thread.start()
    logger.info("task worker started (MAX_GLOBAL_RUNNING=%s)", MAX_GLOBAL_RUNNING)


def stop(timeout: float = 15.0) -> None:
    global _stop_event, _thread
    if _stop_event is not None:
        _stop_event.set()
    if _thread is not None:
        _thread.join(timeout=timeout)
        _thread = None
    logger.info("task worker stopped")


def _loop() -> None:
    assert _stop_event is not None
    while not _stop_event.is_set():
        try:
            job = priority_queue.dequeue(timeout=2)
        except Exception as exc:
            logger.exception("dequeue failed: %s", exc)
            time.sleep(1)
            continue

        if job is None:
            continue

        user_id = job.get("user_id", "unknown")
        task_id = job.get("task_id")
        if not task_id:
            continue

        if not rate_limiter.can_run(user_id):
            priority_queue.enqueue(job)
            time.sleep(0.5)
            continue

        acquired = _semaphore.acquire(blocking=False)
        if not acquired:
            priority_queue.enqueue(job)
            time.sleep(0.5)
            continue

        try:
            logger.info("executing task_id=%s user_id=%s", task_id, user_id)
            task_service.execute_task(task_id)
        except Exception as exc:
            logger.exception("task %s failed: %s", task_id, exc)
        finally:
            _semaphore.release()
