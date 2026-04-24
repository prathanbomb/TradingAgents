"""In-process background task manager with cooperative cancellation."""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages in-process background analysis tasks with cancellation support."""

    def __init__(self):
        self._lock = threading.Lock()
        self._running_job_id: Optional[str] = None
        self._cancel_events: dict[str, threading.Event] = {}

    @property
    def running_job_id(self) -> Optional[str]:
        return self._running_job_id

    def try_acquire(self, job_id: str) -> bool:
        """Try to mark a job as running. Returns False if another job is active."""
        with self._lock:
            if self._running_job_id is not None:
                return False
            self._running_job_id = job_id
            self._cancel_events[job_id] = threading.Event()
            return True

    def release(self, job_id: str):
        """Release the running slot when a job finishes."""
        with self._lock:
            if self._running_job_id == job_id:
                self._running_job_id = None
            self._cancel_events.pop(job_id, None)

    def request_cancel(self, job_id: str) -> bool:
        """Set the cancellation flag for a running job."""
        with self._lock:
            event = self._cancel_events.get(job_id)
            if event:
                event.set()
                return True
            return False

    def is_cancelled(self, job_id: str) -> bool:
        """Check if cancellation was requested for a job."""
        event = self._cancel_events.get(job_id)
        return event is not None and event.is_set()
