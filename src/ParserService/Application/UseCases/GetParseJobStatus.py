from ParserService.Application.Dto.ParseJobStatusView import ParseJobStatusView
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Ports.JobRepository import JobRepository


class GetParseJobStatus:
    """Report the status and failure reason of a job (``GET /v1/parse-jobs/{id}``)."""

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def execute(self, job_id: JobId) -> Result[ParseJobStatusView, ApplicationErrorCode]:
        """Look a job up.

        Args:
            job_id: The job to show.

        Returns:
            The status view, or ``JOB_NOT_FOUND``.
        """
        job = self._repository.get(job_id)
        if job is None:
            return Result.err(ApplicationErrorCode.JOB_NOT_FOUND)
        return Result.ok(ParseJobStatusView.of(job))
