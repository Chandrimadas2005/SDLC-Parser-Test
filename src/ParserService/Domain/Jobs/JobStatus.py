from enum import StrEnum


class JobStatus(StrEnum):
    """Lifecycle of a parse job.

    ``QUEUED`` and ``RUNNING`` are transient. ``SUCCEEDED``, ``PARTIAL`` and ``FAILED``
    are the three result statuses the brief defines for a ``ParsedDocument``.
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Whether the job has finished and will not change again on its own."""
        return self in (JobStatus.SUCCEEDED, JobStatus.PARTIAL, JobStatus.FAILED)
