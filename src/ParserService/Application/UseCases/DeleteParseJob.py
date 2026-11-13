from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Application.UseCases.ArtifactKeys import ArtifactKeys
from ParserService.Application.UseCases.JobServices import JobServices
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobId import JobId


class DeleteParseJob:
    """Delete a job record together with its source and result artifacts."""

    def __init__(self, services: JobServices, keys: ArtifactKeys) -> None:
        self._services = services
        self._keys = keys

    def execute(self, job_id: JobId) -> Result[JobId, ApplicationErrorCode]:
        """Mark, remove artifacts, then remove the job record."""
        job = self._services.repository.get(job_id)
        if job is None:
            return Result.err(ApplicationErrorCode.JOB_NOT_FOUND)
        marked = self._services.repository.update(job.mark_deleting())
        if marked.is_err or not self._remove(job):
            return Result.err(ApplicationErrorCode.STORAGE_UNAVAILABLE)
        return Result.ok(job_id)

    def _remove(self, job: Job) -> bool:
        try:
            self._delete_artifacts(job)
        except OSError:
            return False
        return self._services.repository.delete(job.id)

    def _delete_artifacts(self, job: Job) -> None:
        self._services.store.delete(job.file_pointer)
        if job.result_pointer is not None:
            self._services.store.delete(job.result_pointer)
        markdown = self._keys.result_markdown(job.key.file_hash, job.key.parser_version)
        self._services.store.delete(markdown)
