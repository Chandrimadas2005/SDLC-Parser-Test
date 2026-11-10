from dataclasses import dataclass, replace
from typing import Self

from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer
from ParserService.Domain.Jobs.Duration import Duration
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Domain.Jobs.Instant import Instant
from ParserService.Domain.Jobs.InvalidJobTransitionError import InvalidJobTransitionError
from ParserService.Domain.Jobs.JobCompletion import JobCompletion
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobKey import JobKey
from ParserService.Domain.Jobs.JobStatus import JobStatus


@dataclass(frozen=True, slots=True)
class Job:
    """A parse job record (brief, section 2.7). Immutable; transitions return a new Job.

    The record never holds document content: only identifiers, the file hash, counts,
    timings and pointers into the ArtifactStore.
    """

    id: JobId
    key: JobKey
    file_name: FileName
    file_pointer: ArtifactPointer
    created_at: Instant
    status: JobStatus = JobStatus.QUEUED
    failure_reason: FailureReason | None = None
    attempt_count: int = 0
    result_pointer: ArtifactPointer | None = None
    warning_count: int = 0
    started_at: Instant | None = None
    finished_at: Instant | None = None
    duration: Duration | None = None

    def start(self, now: Instant) -> Self:
        """Begin an attempt: the job becomes running and the attempt counter grows.

        Args:
            now: The moment the worker picked the job up.

        Returns:
            The running job.

        Raises:
            InvalidJobTransitionError: If the job is not queued.
        """
        self._require(JobStatus.QUEUED, "start")
        return replace(
            self,
            status=JobStatus.RUNNING,
            attempt_count=self.attempt_count + 1,
            started_at=now,
            finished_at=None,
            duration=None,
            failure_reason=None,
        )

    def complete(self, completion: JobCompletion, now: Instant) -> Self:
        """Finish a running job with a stored result.

        Args:
            completion: Result status, result pointer and warning count.
            now: The moment the result was saved.

        Returns:
            The finished job.

        Raises:
            InvalidJobTransitionError: If the job is not running.
        """
        self._require(JobStatus.RUNNING, "complete")
        return replace(
            self,
            status=completion.status,
            result_pointer=completion.result_pointer,
            warning_count=completion.warning_count,
            finished_at=now,
            duration=self._elapsed(now),
        )

    def fail(self, reason: FailureReason, now: Instant) -> Self:
        """Finish a job without a result.

        Args:
            reason: Why the job failed, from the fixed enum.
            now: The moment the failure was recorded.

        Returns:
            The failed job.

        Raises:
            InvalidJobTransitionError: If the job has already finished.
        """
        if self.status.is_terminal:
            raise InvalidJobTransitionError(self.status, "fail")
        return replace(
            self,
            status=JobStatus.FAILED,
            failure_reason=reason,
            finished_at=now,
            duration=self._elapsed(now),
        )

    def requeue(self) -> Self:
        """Put a failed job back in the queue for another attempt (manual retry).

        Returns:
            The queued job, keeping its attempt count and history.

        Raises:
            InvalidJobTransitionError: If the job has not failed.
        """
        self._require(JobStatus.FAILED, "requeue")
        return replace(self, status=JobStatus.QUEUED, failure_reason=None)

    def _require(self, expected: JobStatus, transition: str) -> None:
        if self.status is not expected:
            raise InvalidJobTransitionError(self.status, transition)

    def _elapsed(self, now: Instant) -> Duration | None:
        return self.started_at.until(now) if self.started_at is not None else None
