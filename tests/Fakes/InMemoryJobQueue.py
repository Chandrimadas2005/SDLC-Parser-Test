from collections import deque

from ParserService.Domain.Errors import JobQueueError, Result
from ParserService.Domain.Jobs import JobId


class InMemoryJobQueue:
    """Bounded FIFO JobQueue backed by a deque. ``failure`` forces every enqueue to fail."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.failure: JobQueueError | None = None
        self.items: deque[JobId] = deque()

    def enqueue(self, job_id: JobId) -> Result[JobId, JobQueueError]:
        """Queue a job unless the queue is full or a failure is forced."""
        if self.failure is not None:
            return Result.err(self.failure)
        if len(self.items) >= self.capacity:
            return Result.err(JobQueueError.QUEUE_FULL)
        self.items.append(job_id)
        return Result.ok(job_id)

    def claim(self) -> JobId | None:
        """Take the oldest queued job, or ``None``."""
        return self.items.popleft() if self.items else None

    def depth(self) -> int:
        """Number of queued jobs."""
        return len(self.items)
