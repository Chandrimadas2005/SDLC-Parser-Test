from ParserService.Application.Dto.ParseJobSubmitted import ParseJobSubmitted
from ParserService.Application.Dto.SubmitParseJobCommand import SubmitParseJobCommand
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Application.UseCases.ArtifactKeys import ArtifactKeys
from ParserService.Application.UseCases.JobServices import JobServices
from ParserService.Application.UseCases.RetryParseJob import RetryParseJob
from ParserService.Application.UseCases.SubmitPolicy import SubmitPolicy
from ParserService.Domain.Errors.JobQueueError import JobQueueError
from ParserService.Domain.Errors.JobRepositoryError import JobRepositoryError
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileHash import FileHash
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobKey import JobKey


class SubmitParseJob:
    """Accept a file, store it, record the job and queue it (``POST /v1/parse-jobs``).

    Submitting the same bytes again under the same parser version returns the existing
    job. The size limit is checked before anything is stored (brief, section 2.5).
    """

    def __init__(self, services: JobServices, policy: SubmitPolicy, keys: ArtifactKeys) -> None:
        self._services = services
        self._policy = policy
        self._keys = keys

    def execute(
        self, command: SubmitParseJobCommand
    ) -> Result[ParseJobSubmitted, ApplicationErrorCode]:
        """Run the submission.

        Args:
            command: The file name and bytes to parse.

        Returns:
            The job to poll, or ``FILE_TOO_LARGE``, ``QUEUE_FULL`` or
            ``STORAGE_UNAVAILABLE``.
        """
        if len(command.content) > self._policy.max_file_size_bytes:
            return Result.err(ApplicationErrorCode.FILE_TOO_LARGE)
        if self._disk_is_full():
            return Result.err(ApplicationErrorCode.DISK_FULL)
        key = JobKey(FileHash.of(command.content), self._policy.parser_version)
        existing = self._services.repository.find_by_key(key)
        if existing is not None:
            return self._existing(existing, command)
        return self._create(command, key)

    def _existing(
        self, job: Job, command: SubmitParseJobCommand
    ) -> Result[ParseJobSubmitted, ApplicationErrorCode]:
        # A file that failed only for want of a password is parsed again once one is sent.
        locked = job.failure_reason is FailureReason.PASSWORD_PROTECTED
        if command.password is None or not locked:
            return Result.ok(ParseJobSubmitted(job.id, job.status, already_existed=True))
        self._keep_password(job.key, command.password)
        return RetryParseJob(self._services).execute(job.id)

    def _keep_password(self, key: JobKey, password: str | None) -> None:
        if password is not None:
            self._services.store.put(self._keys.password(key.file_hash), password.encode())

    def _disk_is_full(self) -> bool:
        guard = self._services.disk_guard
        if guard is None or guard.disk_space.has_room():
            return False
        guard.temporary_file_cleaner.clean()
        return True

    def _create(
        self, command: SubmitParseJobCommand, key: JobKey
    ) -> Result[ParseJobSubmitted, ApplicationErrorCode]:
        pointer = self._keys.original_file(key.file_hash, command.file_name)
        self._services.store.put(pointer, command.content)
        self._keep_password(key, command.password)
        job = Job(JobId.new(), key, command.file_name, pointer, self._services.clock.now())
        added = self._services.repository.add(job)
        if added.is_err:
            return self._after_add_failure(added.unwrap_err(), key)
        return self._enqueue(job)

    def _after_add_failure(
        self, error: JobRepositoryError, key: JobKey
    ) -> Result[ParseJobSubmitted, ApplicationErrorCode]:
        if error is JobRepositoryError.DUPLICATE_KEY:
            raced = self._services.repository.find_by_key(key)
            if raced is not None:
                return Result.ok(ParseJobSubmitted(raced.id, raced.status, already_existed=True))
        return Result.err(ApplicationErrorCode.STORAGE_UNAVAILABLE)

    def _enqueue(self, job: Job) -> Result[ParseJobSubmitted, ApplicationErrorCode]:
        queued = self._services.queue.enqueue(job.id)
        if queued.is_ok:
            return Result.ok(ParseJobSubmitted(job.id, job.status, already_existed=False))
        self._services.repository.delete(job.id)
        self._services.store.delete(job.file_pointer)
        if queued.unwrap_err() is JobQueueError.QUEUE_FULL:
            return Result.err(ApplicationErrorCode.QUEUE_FULL)
        return Result.err(ApplicationErrorCode.STORAGE_UNAVAILABLE)
