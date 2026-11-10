from typing import Protocol

from ParserService.Domain.Errors.JobRepositoryError import JobRepositoryError
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobKey import JobKey


class JobRepository(Protocol):
    """Persistence of job records. The only way any layer reaches the database.

    Implementations live in Infrastructure (PostgreSQL in production, SQLite locally).
    They store identifiers, hashes, counts, timings and pointers, never document content.
    """

    def add(self, job: Job) -> Result[Job, JobRepositoryError]:
        """Insert a new job record.

        Args:
            job: The job to store; its key must not already exist.

        Returns:
            The stored job, or ``DUPLICATE_KEY`` when the same file and parser version
            was stored concurrently, or ``STORE_UNAVAILABLE`` on a transient outage.
        """
        ...

    def get(self, job_id: JobId) -> Job | None:
        """Load a job by identifier.

        Args:
            job_id: The job to look up.

        Returns:
            The job, or ``None`` when no such job exists.
        """
        ...

    def find_by_key(self, key: JobKey) -> Job | None:
        """Load the job for a file hash and parser version, if one was ever submitted.

        Args:
            key: File hash plus parser version.

        Returns:
            The existing job, or ``None``.
        """
        ...

    def update(self, job: Job) -> Result[Job, JobRepositoryError]:
        """Overwrite the record of an existing job with its new state.

        Args:
            job: The job in its new state.

        Returns:
            The stored job, or ``NOT_FOUND`` when the record no longer exists.
        """
        ...

    def delete(self, job_id: JobId) -> bool:
        """Remove a job record.

        Args:
            job_id: The job to remove.

        Returns:
            ``True`` when a record was removed, ``False`` when none existed.
        """
        ...
