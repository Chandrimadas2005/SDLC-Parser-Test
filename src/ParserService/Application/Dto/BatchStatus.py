from enum import StrEnum


class BatchStatus(StrEnum):
    """Overall state of a multi-file upload, derived from its jobs."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
