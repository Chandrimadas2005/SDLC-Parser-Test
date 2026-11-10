from enum import StrEnum


class JobQueueError(StrEnum):
    """Expected reasons a job cannot be queued."""

    QUEUE_FULL = "queue_full"
    QUEUE_UNAVAILABLE = "queue_unavailable"
