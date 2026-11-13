import os
import signal
import threading
from types import FrameType

import structlog

from ParserService.Infrastructure.Bootstrap.ServiceContainer import ServiceContainer
from ParserService.Infrastructure.Bootstrap.WorkerLoop import WorkerLoop
from ParserService.Infrastructure.Config.Settings import Settings
from ParserService.Infrastructure.Logging.LoggingConfigurator import LoggingConfigurator


class WorkerRunner:
    """Process entry point of the isolated parser worker."""

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
        structlog.get_logger(__name__).info(
            "worker_started", parser_version=container.parser_version.value
        )
        WorkerLoop(container.process_next_job(), runner.stop, container.retention_cleanup()).run()

    def request_stop(self, signal_number: int, frame: FrameType | None) -> None:
        """Stop after the current job completes."""
        del signal_number, frame
        self.stop.set()
