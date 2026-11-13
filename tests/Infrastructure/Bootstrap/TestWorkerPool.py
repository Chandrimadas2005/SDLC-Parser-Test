import threading
import time
from pathlib import Path
from typing import ClassVar

import pytest

from ParserService.Application.UseCases import ProcessNextJob
from ParserService.Infrastructure.Bootstrap import WorkerConcurrency, WorkerLoop, WorkerPool
from ParserService.Infrastructure.Config import EnvironmentVariable


class _SlowJobs(ProcessNextJob):
    """Stands in for the use case: each job takes a moment; tracks how many run at once."""

    def __init__(self, jobs: int, stop: threading.Event) -> None:
        self._left, self._stop = jobs, stop
        self.active = self.peak = self.done = 0
        self._lock = threading.Lock()

    def execute(self) -> bool:
        with self._lock:
            if self._left == 0:
                return False
            self._left -= 1
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.2)
        with self._lock:
            self.active -= 1
            self.done += 1
            if self._left == 0 and self.active == 0:
                self._stop.set()
        return True


class _EightGigabytes(WorkerConcurrency):
    def available_mb(self) -> int:
        return 8 * 1024


class _NoCgroup(WorkerConcurrency):
    CGROUP_MEMORY: ClassVar[Path] = Path("/nonexistent/memory.max")


class TestWorkerPool:
    """Several jobs run at once up to the slot limit; the rest wait and start by themselves."""

    def test_jobs_run_concurrently_up_to_the_slot_limit(self) -> None:
        stop = threading.Event()
        jobs = _SlowJobs(10, stop)
        loops = [WorkerLoop(jobs, stop) for _ in range(4)]

        started = time.monotonic()
        processed = WorkerPool(loops).run()

        assert processed == 10
        assert jobs.peak == 4
        assert time.monotonic() - started < 10 * 0.2

    def test_concurrency_follows_memory_unless_configured(self) -> None:
        concurrency = _EightGigabytes()

        assert concurrency.resolve({}, job_memory_mb=1024) == 7
        assert concurrency.resolve({}, job_memory_mb=4096) == 1
        configured = {str(EnvironmentVariable.WORKER_CONCURRENCY): "3"}
        assert concurrency.resolve(configured, job_memory_mb=1024) == 3
        with pytest.raises(ValueError, match="positive"):
            concurrency.resolve({str(EnvironmentVariable.WORKER_CONCURRENCY): "0"}, 1024)

    def test_machine_memory_is_used_without_a_container_limit(self) -> None:
        assert _NoCgroup().available_mb() > 0
        assert _NoCgroup().from_memory(1) >= 1
