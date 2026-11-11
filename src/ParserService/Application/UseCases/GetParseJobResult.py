from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Ports.ArtifactStore import ArtifactStore
from ParserService.Domain.Ports.JobRepository import JobRepository


class GetParseJobResult:
    """Read the JSON result artifact for a completed parse job."""

    def __init__(self, repository: JobRepository, store: ArtifactStore) -> None:
        self._repository = repository
        self._store = store

    def execute(self, job_id: JobId) -> Result[bytes, ApplicationErrorCode]:
        """Return the stored result bytes or a stable API error code."""
        job = self._repository.get(job_id)
        if job is None:
            return Result.err(ApplicationErrorCode.JOB_NOT_FOUND)
        if job.result_pointer is None:
            return Result.err(ApplicationErrorCode.RESULT_NOT_READY)
        content = self._store.read(job.result_pointer)
        if content is None:
            return Result.err(ApplicationErrorCode.RESULT_NOT_FOUND)
        return Result.ok(content)
