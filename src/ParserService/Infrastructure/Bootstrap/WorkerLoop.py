import threading
from typing import Final

import structlog

from ParserService.Application.UseCases.ProcessNextJob import ProcessNextJob


class WorkerLoop:
    """Processes queued jobs one after another until it is told to stop.

    When the queue is empty it waits briefly, waking up at once if it is stopped.
    It logs counts only, never document content.
    """

    IDLE_SECONDS: Final = 1.0

    def __init__(self, use_case: ProcessNextJob, stop: threading.Event) -> None:
        self._use_case = use_case
        self._stop = stop
        self._log = structlog.get_logger(__name__)

    def run(self) -> int:
        """Process jobs until the stop event is set.

        Returns:
            How many jobs were processed.
        """
        processed = 0
        while not self._stop.is_set():
            drained = self.drain()
            processed += drained
            if drained == 0:
                self._stop.wait(self.IDLE_SECONDS)
        self._log.info("worker_stopped", jobs_processed=processed)
        return processed

    def drain(self) -> int:
        """Process jobs until the queue is empty or the loop is stopped.

        Returns:
            How many jobs were processed.
        """
        processed = 0
        while not self._stop.is_set() and self._use_case.execute():
            processed += 1
        return processed
