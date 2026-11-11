from ParserService.Application.Dto.ParseJobSubmitted import ParseJobSubmitted
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Application.UseCases.JobServices import JobServices
from ParserService.Domain.Errors.JobQueueError import JobQueueError
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobStatus import JobStatus


class RetryParseJob:
    """Requeue a failed job for another isolated parse attempt."""

    def __init__(self, services: JobServices) -> None:
        self._services = services

    def execute(self, job_id: JobId) -> Result[ParseJobSubmitted, ApplicationErrorCode]:
        """Requeue a failed job, preserving its original file and identity."""
        job = self._services.repository.get(job_id)
        if job is None:
            return Result.err(ApplicationErrorCode.JOB_NOT_FOUND)
        if job.status is not JobStatus.FAILED:
            return Result.err(ApplicationErrorCode.RETRY_NOT_ALLOWED)
        queued = job.requeue()
        if self._services.repository.update(queued).is_err:
            return Result.err(ApplicationErrorCode.STORAGE_UNAVAILABLE)
        return self._enqueue(queued, job)

    def _enqueue(self, queued: Job, original: Job) -> Result[ParseJobSubmitted, ApplicationErrorCode]:
        result = self._services.queue.enqueue(queued.id)
        if result.is_ok:
            return Result.ok(ParseJobSubmitted(queued.id, queued.status, already_existed=False))
        reverted = self._services.repository.update(original)
        if reverted.is_err:
            return Result.err(ApplicationErrorCode.STORAGE_UNAVAILABLE)
        if result.unwrap_err() is JobQueueError.QUEUE_FULL:
            return Result.err(ApplicationErrorCode.QUEUE_FULL)
        return Result.err(ApplicationErrorCode.STORAGE_UNAVAILABLE)
