from dataclasses import dataclass
from typing import Self

from ParserService.Domain.Jobs.Duration import Duration
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.Instant import Instant
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobStatus import JobStatus
from ParserService.Domain.Jobs.ParserVersion import ParserVersion


@dataclass(frozen=True, slots=True)
class ParseJobStatusView:
    """What a caller sees when polling a job: status, failure reason and timings."""

    job_id: JobId
    status: JobStatus
    parser_version: ParserVersion
    failure_reason: FailureReason | None
    attempt_count: int
    warning_count: int
    has_result: bool
    created_at: Instant
    started_at: Instant | None
    finished_at: Instant | None
    duration: Duration | None

    @classmethod
    def of(cls, job: Job) -> Self:
        """Project a job record onto the view.

        Args:
            job: The job to show.

        Returns:
            The caller-facing view of the job.
        """
        return cls(
            job_id=job.id,
            status=job.status,
            parser_version=job.key.parser_version,
            failure_reason=job.failure_reason,
            attempt_count=job.attempt_count,
            warning_count=job.warning_count,
            has_result=job.result_pointer is not None,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            duration=job.duration,
        )
