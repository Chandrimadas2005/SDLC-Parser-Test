from dataclasses import dataclass

from ParserService.Infrastructure.Resilience.BackoffExecutor import BackoffExecutor


@dataclass(frozen=True, slots=True)
class QueuePolicy:
    """Queue capacity and transient database retry behavior."""

    capacity: int
    backoff: BackoffExecutor
