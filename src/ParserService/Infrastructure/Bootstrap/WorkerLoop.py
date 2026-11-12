import threading
import time
from typing import Final

import structlog

from ParserService.Application.UseCases.ProcessNextJob import ProcessNextJob
from ParserService.Application.UseCases.RetentionCleanup import RetentionCleanup


class WorkerLoop:
    """Process queued jobs and periodically clean expired artifacts."""

    IDLE_SECONDS: Final = 1.0
    CLEANUP_INTERVAL_SECONDS: Final = 3_600.0

    def __init__(
        self,
        use_case: ProcessNextJob,
        stop: threading.Event,
        cleanup: RetentionCleanup | None = None,
    ) -> None:
        self._use_case = use_case
        self._stop = stop
        self._cleanup = cleanup
        self._log = structlog.get_logger(__name__)

    def run(self) -> int:
        """Process queued jobs until stopped, running cleanup once per hour."""
        processed = 0
        next_cleanup = 0.0
        while not self._stop.is_set():
            next_cleanup = self._clean_if_due(next_cleanup)
            drained = self.drain()
            processed += drained
            if drained == 0:
                self._stop.wait(self.IDLE_SECONDS)
        self._log.info("worker_stopped", jobs_processed=processed)
        return processed

    def _clean_if_due(self, next_cleanup: float) -> float:
        if self._cleanup is None or time.monotonic() < next_cleanup:
            return next_cleanup
        deleted = self._cleanup.execute()
        self._log.info("worker_expired_jobs_cleaned", jobs=deleted)
        return time.monotonic() + self.CLEANUP_INTERVAL_SECONDS

    def drain(self) -> int:
        """Process jobs until the queue is empty or the loop is stopped."""
        processed = 0
        while not self._stop.is_set() and self._use_case.execute():
            processed += 1
        return processed
