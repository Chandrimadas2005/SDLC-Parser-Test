from ParserService.Domain.Errors import JobRepositoryError, Result
from ParserService.Domain.Jobs import Instant, Job, JobId, JobKey, JobStatus


class InMemoryJobRepository:
    """JobRepository backed by dictionaries, with the unique key rule enforced.

    ``failure`` forces every ``add`` to return that error, to simulate outages. ``racer``
    simulates another process inserting that job between ``find_by_key`` and ``add``.
    """

    def __init__(self) -> None:
        self.jobs: dict[JobId, Job] = {}
        self.failure: JobRepositoryError | None = None
        self.racer: Job | None = None

    def add(self, job: Job) -> Result[Job, JobRepositoryError]:
        """Insert a job unless its key exists, a failure is forced or a racer wins."""
        if self.failure is not None:
            return Result.err(self.failure)
        if self.racer is not None:
            self.jobs[self.racer.id] = self.racer
            return Result.err(JobRepositoryError.DUPLICATE_KEY)
        if self.find_by_key(job.key) is not None:
            return Result.err(JobRepositoryError.DUPLICATE_KEY)
        self.jobs[job.id] = job
        return Result.ok(job)

    def get(self, job_id: JobId) -> Job | None:
        """Load a job by identifier."""
        return self.jobs.get(job_id)

    def find_by_key(self, key: JobKey) -> Job | None:
        """Load a job by file hash and parser version."""
        return next((job for job in self.jobs.values() if job.key == key), None)

    def update(self, job: Job) -> Result[Job, JobRepositoryError]:
        """Replace a stored job."""
        if job.id not in self.jobs:
            return Result.err(JobRepositoryError.NOT_FOUND)
        self.jobs[job.id] = job
        return Result.ok(job)

    def list_by_status(self, status: JobStatus) -> list[Job]:
        """List jobs in the requested state."""
        return [job for job in self.jobs.values() if job.status is status]

    def list_created_before(self, cutoff: Instant) -> list[Job]:
        """List jobs older than the retention cutoff."""
        return [job for job in self.jobs.values() if job.created_at < cutoff]

    def delete(self, job_id: JobId) -> bool:
        """Remove a job; ``True`` when one existed."""
        return self.jobs.pop(job_id, None) is not None
