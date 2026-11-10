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
    """Process entry point of the worker: ``parser-worker`` (see ``pyproject.toml``).

    Each job is parsed in its own short-lived process with time and memory limits;
    this long-lived process only takes jobs from the queue and records results.
    SIGTERM and SIGINT stop it after the current job.
    """

    def __init__(self) -> None:
        self.stop = threading.Event()

    @classmethod
    def main(cls) -> None:
        """Run the worker until it receives SIGTERM or SIGINT."""
        settings = Settings.from_environment(os.environ)
        LoggingConfigurator().configure(settings.log_level)
        container = ServiceContainer(settings)
        container.migrate()
        runner = cls()
        signal.signal(signal.SIGTERM, runner.request_stop)
        signal.signal(signal.SIGINT, runner.request_stop)
        structlog.get_logger(__name__).info(
            "worker_started", parser_version=container.parser_version.value
        )
        WorkerLoop(container.process_next_job(), runner.stop).run()

    def request_stop(self, signal_number: int, frame: FrameType | None) -> None:
        """Signal handler: finish the current job, then stop.

        Args:
            signal_number: The signal received.
            frame: The interrupted frame (unused).
        """
        del signal_number, frame
        self.stop.set()
