from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest

from ParserService.Infrastructure.Logging.MetricLabel import MetricLabel


class ServiceMetrics:
    """Prometheus metrics for the service, on a private registry so tests stay isolated."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self._submissions = Counter(
            "parser_job_submissions_total",
            "Parse job submissions by outcome",
            [MetricLabel.OUTCOME],
            registry=self.registry,
        )
        self._queue_depth = Gauge(
            "parser_queue_depth", "Jobs waiting to be claimed", registry=self.registry
        )

    def record_submission(self, outcome: str) -> None:
        """Count one submission.

        Args:
            outcome: ``created``, ``existing`` or an error code.
        """
        self._submissions.labels(outcome).inc()

    def set_queue_depth(self, depth: int) -> None:
        """Publish the current queue depth.

        Args:
            depth: Number of queued jobs.
        """
        self._queue_depth.set(depth)

    def render(self) -> bytes:
        """Render every metric in the Prometheus text exposition format.

        Returns:
            The scrape body.
        """
        return generate_latest(self.registry)
