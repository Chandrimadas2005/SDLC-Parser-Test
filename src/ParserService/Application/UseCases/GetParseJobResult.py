from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobStatus import JobStatus
from ParserService.Domain.Ports.ArtifactStore import ArtifactStore
from ParserService.Domain.Ports.JobRepository import JobRepository


class GetParseJobResult:
    """Read the JSON result artifact for a completed parse job."""

    def __init__(self, repository: JobRepository, store: ArtifactStore) -> None:
        self._repository = repository
        self._store = store

    def execute(self, job_id: JobId) -> Result[bytes, ApplicationErrorCode]:
        """Return the stored result bytes or a stable API error code.

        Args:
            job_id: The job whose result is read.

        Returns:
            The result bytes, ``JOB_NOT_FOUND``, ``JOB_FAILED`` (the job failed and will
            never have a result), ``RESULT_NOT_READY`` (still queued or running) or
            ``RESULT_NOT_FOUND`` (the stored artifact is missing).
        """
        job = self._repository.get(job_id)
        if job is None:
            return Result.err(ApplicationErrorCode.JOB_NOT_FOUND)
        if job.result_pointer is None:
            return Result.err(self._missing(job.status))
        content = self._store.read(job.result_pointer)
        if content is None:
            return Result.err(ApplicationErrorCode.RESULT_NOT_FOUND)
        return Result.ok(content)

    @staticmethod
    def _missing(status: JobStatus) -> ApplicationErrorCode:
        if status is JobStatus.FAILED:
            return ApplicationErrorCode.JOB_FAILED
        return ApplicationErrorCode.RESULT_NOT_READY
