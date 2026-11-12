from ParserService.Application.UseCases.JobServices import JobServices
from ParserService.Domain.Jobs.JobStatus import JobStatus


class RecoverRunningJobs:
    """Return worker-abandoned jobs to the durable queue on startup."""

    def __init__(self, services: JobServices) -> None:
        self._services = services

    def execute(self) -> int:
        """Recover all running jobs and return the number examined."""
        jobs = self._services.repository.list_by_status(JobStatus.RUNNING)
        for job in jobs:
            recovered = job.recover(self._services.max_attempts, self._services.clock.now())
            self._services.repository.update(recovered)
        return len(jobs)
