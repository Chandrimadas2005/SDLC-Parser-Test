from typing import Self

from pydantic import BaseModel, ConfigDict

from ParserService.Application.Dto.ParseJobStatusView import ParseJobStatusView
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.Instant import Instant
from ParserService.Domain.Jobs.JobStatus import JobStatus


class ParseJobStatusResponse(BaseModel):
    """Body of ``GET /v1/parse-jobs/{id}``. Times are UTC epoch milliseconds."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    status: JobStatus
    parser_version: str
    failure_reason: FailureReason | None
    attempt_count: int
    warning_count: int
    has_result: bool
    created_at: int
    started_at: int | None
    finished_at: int | None
    duration_ms: int | None

    @classmethod
    def of(cls, view: ParseJobStatusView) -> Self:
        """Build the response from the use case view.

        Args:
            view: What the use case returned.

        Returns:
            The response body.
        """
        return cls(
            job_id=view.job_id.value,
            status=view.status,
            parser_version=view.parser_version.value,
            failure_reason=view.failure_reason,
            attempt_count=view.attempt_count,
            warning_count=view.warning_count,
            has_result=view.has_result,
            created_at=view.created_at.epoch_ms,
            started_at=cls._epoch(view.started_at),
            finished_at=cls._epoch(view.finished_at),
            duration_ms=view.duration.milliseconds if view.duration is not None else None,
        )

    @staticmethod
    def _epoch(instant: Instant | None) -> int | None:
        return instant.epoch_ms if instant is not None else None
