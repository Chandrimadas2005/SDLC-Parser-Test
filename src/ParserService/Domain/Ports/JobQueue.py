from typing import Protocol

from ParserService.Domain.Errors.JobQueueError import JobQueueError
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.JobId import JobId


class JobQueue(Protocol):
    """Hands queued jobs to workers, one at a time, each to exactly one worker.

    The queue is bounded: when it is full, ``enqueue`` returns ``QUEUE_FULL`` and the
    API answers 429 with ``Retry-After`` (brief, section 2.5).
    """

    def enqueue(self, job_id: JobId) -> Result[JobId, JobQueueError]:
        """Make a job available to workers.

        Args:
            job_id: The job to queue; its record must already be stored.

        Returns:
            The queued job identifier, or why it was refused.
        """
        ...

    def claim(self) -> JobId | None:
        """Take the next job for processing, so no other worker can take it.

        Returns:
            The claimed job identifier, or ``None`` when the queue is empty.
        """
        ...

    def depth(self) -> int:
        """Count the jobs waiting to be claimed.

        Returns:
            The number of queued jobs.
        """
        ...
