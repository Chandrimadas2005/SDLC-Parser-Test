import errno
from typing import ClassVar

from ParserService.Application.UseCases.ArtifactKeys import ArtifactKeys
from ParserService.Application.UseCases.JobServices import JobServices
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobCompletion import JobCompletion
from ParserService.Domain.Jobs.JobStatus import JobStatus
from ParserService.Domain.Ports.DocumentParser import DocumentParser


class ProcessNextJob:
    """Take a queued job, parse it in isolation and persist its outcome."""

    TRANSIENT_REASONS = frozenset(
        {FailureReason.TIMEOUT, FailureReason.EXTRACTOR_CRASH, FailureReason.STORAGE_ERROR}
    )
    TRANSIENT_STORAGE_ERRNOS: ClassVar[frozenset[int]] = frozenset(
        {
            errno.EAGAIN,
            errno.EINTR,
            errno.EIO,
            errno.ECONNRESET,
            errno.ETIMEDOUT,
            errno.ECONNREFUSED,
            errno.EPIPE,
            errno.ENETDOWN,
            errno.ENETUNREACH,
        }
    )

    def __init__(self, services: JobServices, parser: DocumentParser, keys: ArtifactKeys) -> None:
        self._services = services
        self._parser = parser
        self._keys = keys

    def execute(self) -> bool:
        """Process one queued job, returning whether the queue had an item."""
        job_id = self._services.queue.claim()
        if job_id is None:
            return False
        job = self._services.repository.get(job_id)
        if job is not None:
            self._process(self._running(job))
        return True

    def _running(self, job: Job) -> Job:
        if job.status is JobStatus.RUNNING:
            return job
        return job.start(self._services.clock.now())

    def _process(self, job: Job) -> None:
        parsed = self._parser.parse(job.file_pointer, job.file_name)
        if parsed.is_err:
            self._record_failure(job, parsed.unwrap_err())
            return
        outcome = parsed.unwrap()
        pointer = self._keys.result_json(job.key.file_hash, job.key.parser_version)
        try:
            self._services.store.put(pointer, outcome.content)
        except OSError as error:
            self._record_failure(job, self._storage_reason(error))
            return
        completion = JobCompletion(JobStatus(outcome.status.value), pointer, outcome.warning_count)
        self._services.repository.update(job.complete(completion, self._services.clock.now()))

    def _record_failure(self, job: Job, reason: FailureReason) -> None:
        now = self._services.clock.now()
        terminal_reason = self._terminal_reason(job, reason)
        failed = job.fail(terminal_reason, now)
        self._services.repository.update(failed)
        if terminal_reason is not reason or reason not in self.TRANSIENT_REASONS:
            return
        if job.attempt_count >= self._services.max_attempts:
            return
        queued = failed.requeue()
        if self._services.repository.update(queued).is_ok:
            self._services.queue.enqueue(queued.id)

    @classmethod
    def _storage_reason(cls, error: OSError) -> FailureReason:
        if error.errno in cls.TRANSIENT_STORAGE_ERRNOS:
            return FailureReason.STORAGE_ERROR
        return FailureReason.STORAGE_PERMANENT_ERROR

    def _terminal_reason(self, job: Job, reason: FailureReason) -> FailureReason:
        if reason in self.TRANSIENT_REASONS and job.attempt_count >= self._services.max_attempts:
            return FailureReason.MAX_ATTEMPTS_EXCEEDED
        return reason
