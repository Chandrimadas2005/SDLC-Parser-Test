import threading
from collections.abc import Sequence

import structlog

from ParserService.Infrastructure.Bootstrap.WorkerLoop import WorkerLoop


class WorkerPool:
    """Runs several worker loops side by side, one thread each.

    Every loop claims jobs from the same database queue, which hands each job to
    exactly one claimer, so N loops parse up to N files at the same time. Each job
    still runs in its own isolated process with its own time and memory limits.
    When a loop finishes a job it claims the next queued one by itself, so jobs that
    arrived while every slot was busy start as soon as a slot frees up.
    """

    def __init__(self, loops: Sequence[WorkerLoop]) -> None:
        self._loops = loops
        self._processed: list[int] = []
        self._lock = threading.Lock()

    def run(self) -> int:
        """Run every loop until they are all stopped.

        Returns:
            How many jobs the pool processed in total.
        """
        threads = [
            threading.Thread(target=self._run_loop, args=(loop,), name=f"worker-slot-{n}")
            for n, loop in enumerate(self._loops, 1)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        total = sum(self._processed)
        structlog.get_logger(__name__).info("worker_pool_stopped", jobs_processed=total)
        return total

    def _run_loop(self, loop: WorkerLoop) -> None:
        processed = loop.run()
        with self._lock:
            self._processed.append(processed)
