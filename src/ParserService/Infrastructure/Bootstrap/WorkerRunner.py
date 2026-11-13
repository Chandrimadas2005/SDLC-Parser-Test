import os
import signal
import threading
from types import FrameType

import structlog

from ParserService.Infrastructure.Bootstrap.ServiceContainer import ServiceContainer
from ParserService.Infrastructure.Bootstrap.WorkerConcurrency import WorkerConcurrency
from ParserService.Infrastructure.Bootstrap.WorkerLoop import WorkerLoop
from ParserService.Infrastructure.Bootstrap.WorkerPool import WorkerPool
from ParserService.Infrastructure.Config.Settings import Settings
from ParserService.Infrastructure.Logging.LoggingConfigurator import LoggingConfigurator


class WorkerRunner:
    """Process entry point of the parser worker: a pool of loops sized by memory or setting."""

    def __init__(self) -> None:
        self.stop = threading.Event()

    @classmethod
    def main(cls) -> None:
        """Recover unfinished jobs and run the durable worker loop."""
        settings = Settings.from_environment(os.environ)
        LoggingConfigurator().configure(settings.log_level)
        container = ServiceContainer(settings)
        container.migrate()
        recovered = container.recover_running_jobs()
        structlog.get_logger(__name__).info("worker_jobs_recovered", jobs=recovered)
        runner = cls()
        signal.signal(signal.SIGTERM, runner.request_stop)
        signal.signal(signal.SIGINT, runner.request_stop)
        slots = WorkerConcurrency().resolve(os.environ, settings.limits.job_memory_limit_mb)
        structlog.get_logger(__name__).info(
            "worker_started", parser_version=container.parser_version.value, slots=slots
        )
        runner.pool(container, slots).run()

    def pool(self, container: ServiceContainer, slots: int) -> WorkerPool:
        """Build ``slots`` worker loops; only the first one runs retention cleanup.

        Args:
            container: The wired services.
            slots: How many jobs to parse at the same time.

        Returns:
            The pool, ready to run.
        """
        use_case, cleanup = container.process_next_job(), container.retention_cleanup()
        loops = [WorkerLoop(use_case, self.stop, cleanup if n == 0 else None) for n in range(slots)]
        return WorkerPool(loops)

    def request_stop(self, signal_number: int, frame: FrameType | None) -> None:
        """Stop after the current job completes."""
        del signal_number, frame
        self.stop.set()
