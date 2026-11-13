from ParserService.Application.Dto.ParseJobStatusView import ParseJobStatusView
from ParserService.Domain.Jobs.JobStatus import JobStatus
from ParserService.Domain.Ports.JobRepository import JobRepository


class GetFailedParseJobs:
    """Return persisted failed jobs for the failed-jobs API."""

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def execute(self) -> list[ParseJobStatusView]:
        """List failed jobs, oldest first."""
        jobs = self._repository.list_by_status(JobStatus.FAILED)
        return [ParseJobStatusView.of(job) for job in jobs]
