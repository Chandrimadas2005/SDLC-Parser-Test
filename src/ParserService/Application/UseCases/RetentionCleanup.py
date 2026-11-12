from ParserService.Application.UseCases.ArtifactKeys import ArtifactKeys
from ParserService.Application.UseCases.JobServices import JobServices
from ParserService.Domain.Jobs.Instant import Instant
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobStatus import JobStatus


class RetentionCleanup:
    """Delete expired jobs and their artifacts from the Parser-owned stores."""

    DAY_MILLISECONDS = 86_400_000

    def __init__(self, services: JobServices, keys: ArtifactKeys, retention_days: int) -> None:
        self._services = services
        self._keys = keys
        self._retention_days = retention_days

    def execute(self) -> int:
        """Delete all jobs older than retention_days and return the deleted count."""
        now = self._services.clock.now()
        cutoff = Instant(max(0, now.epoch_ms - self._retention_days * self.DAY_MILLISECONDS))
        expired = self._services.repository.list_created_before(cutoff)
        pending = self._services.repository.list_by_status(JobStatus.DELETING)
        jobs = {job.id: job for job in expired}
        jobs.update({job.id: job for job in pending})
        return sum(self._delete(job) for job in jobs.values())

    def _delete(self, job: Job) -> int:
        marked = self._services.repository.update(job.mark_deleting())
        if marked.is_err:
            return 0
        try:
            self._services.store.delete(job.file_pointer)
            if job.result_pointer is not None:
                self._services.store.delete(job.result_pointer)
            markdown = self._keys.result_markdown(job.key.file_hash, job.key.parser_version)
            self._services.store.delete(markdown)
        except OSError:
            return 0
        return int(self._services.repository.delete(job.id))
