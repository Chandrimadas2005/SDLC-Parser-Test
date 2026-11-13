from dataclasses import dataclass

from ParserService.Application.Dto.BatchFileView import BatchFileView
from ParserService.Application.Dto.BatchStatus import BatchStatus
from ParserService.Domain.Jobs.BatchId import BatchId
from ParserService.Domain.Jobs.JobStatus import JobStatus


@dataclass(frozen=True, slots=True)
class ParseBatchView:
    """A batch as the caller sees it: every file's job, in upload order."""

    batch_id: BatchId
    files: tuple[BatchFileView, ...]

    @property
    def status(self) -> BatchStatus:
        """``running`` until every job has finished; then succeeded, partial or failed."""
        statuses = [file.status.status for file in self.files]
        if any(status in {JobStatus.QUEUED, JobStatus.RUNNING} for status in statuses):
            return BatchStatus.RUNNING
        failed = sum(status is JobStatus.FAILED for status in statuses)
        if failed == 0:
            return BatchStatus.SUCCEEDED
        return BatchStatus.FAILED if failed == len(statuses) else BatchStatus.PARTIAL

    @property
    def finished(self) -> bool:
        """Whether every job has finished."""
        return self.status is not BatchStatus.RUNNING
