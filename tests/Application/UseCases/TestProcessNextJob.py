import pytest

from ParserService.Application.UseCases import ArtifactKeys, JobServices, ProcessNextJob
from ParserService.Domain.Documents import DocumentStatus, ParseOutcome
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import (
    ArtifactPointer,
    Duration,
    FailureReason,
    FileHash,
    FileName,
    Instant,
    Job,
    JobId,
    JobKey,
    JobStatus,
    ParserVersion,
)
from tests.Fakes import (
    FakeDocumentParser,
    FixedClock,
    InMemoryArtifactStore,
    InMemoryJobQueue,
    InMemoryJobRepository,
)

KEY = JobKey(FileHash.of(b"notes"), ParserVersion("0.1.0"))
JOB = Job(
    JobId.new(), KEY, FileName("notes.txt"), ArtifactPointer("files/x/original.txt"), Instant(0)
)
OUTCOME = ParseOutcome(DocumentStatus.PARTIAL, 2, b'{"status": "partial"}')


class TestProcessNextJob:
    """The worker parses queued jobs and records results, writing the file first."""

    @staticmethod
    def _run(
        result: Result[ParseOutcome, FailureReason], *, queued: bool = True, max_attempts: int = 3
    ) -> tuple[ProcessNextJob, InMemoryJobRepository, InMemoryArtifactStore]:
        repository, store, queue = (
            InMemoryJobRepository(),
            InMemoryArtifactStore(),
            InMemoryJobQueue(5),
        )
        repository.add(JOB)
        if queued:
            queue.enqueue(JOB.id)
        services = JobServices(repository, store, queue, FixedClock(Instant(1_500)), max_attempts)
        return (
            ProcessNextJob(services, FakeDocumentParser(result), ArtifactKeys()),
            repository,
            store,
        )

    def test_empty_queue_does_nothing(self) -> None:
        use_case, repository, _ = self._run(Result.ok(OUTCOME), queued=False)

        assert use_case.execute() is False
        assert repository.jobs[JOB.id].status is JobStatus.QUEUED

    def test_success_stores_the_result_then_completes_the_job(self) -> None:
        use_case, repository, store = self._run(Result.ok(OUTCOME))

        assert use_case.execute() is True

        job = repository.jobs[JOB.id]
        assert job.status is JobStatus.PARTIAL
        assert job.warning_count == 2
        assert job.attempt_count == 1
        assert job.duration == Duration(1_500 - 1_500)
        assert job.result_pointer == ArtifactKeys().result_json(KEY.file_hash, KEY.parser_version)
        assert store.read(job.result_pointer) == OUTCOME.content

    def test_transient_failure_is_automatically_requeued(self) -> None:
        use_case, repository, store = self._run(Result.err(FailureReason.TIMEOUT))

        use_case.execute()

        job = repository.jobs[JOB.id]
        assert job.status is JobStatus.QUEUED
        assert job.failure_reason is None
        assert job.attempt_count == 1
        assert store.artifacts == {}

    def test_transient_failure_exhausts_attempts(self) -> None:
        use_case, repository, _ = self._run(Result.err(FailureReason.TIMEOUT), max_attempts=1)

        use_case.execute()

        job = repository.jobs[JOB.id]
        assert job.status is JobStatus.FAILED
        assert job.failure_reason is FailureReason.MAX_ATTEMPTS_EXCEEDED

    def test_permanent_failure_is_not_retried(self) -> None:
        use_case, repository, _ = self._run(Result.err(FailureReason.CORRUPTED_FILE))

        use_case.execute()

        job = repository.jobs[JOB.id]
        assert job.status is JobStatus.FAILED
        assert job.failure_reason is FailureReason.CORRUPTED_FILE

    def test_an_already_running_job_is_not_started_twice(self) -> None:
        use_case, repository, _ = self._run(Result.ok(OUTCOME))
        repository.jobs[JOB.id] = JOB.start(Instant(1_000))

        use_case.execute()

        assert repository.jobs[JOB.id].attempt_count == 1
        assert repository.jobs[JOB.id].duration == Duration(500)

    def test_a_claimed_job_that_vanished_is_skipped(self) -> None:
        use_case, repository, _ = self._run(Result.ok(OUTCOME))
        repository.delete(JOB.id)

        assert use_case.execute() is True

    def test_outcome_rejects_failed_status_and_negative_counts(self) -> None:
        with pytest.raises(ValueError, match="no outcome"):
            ParseOutcome(DocumentStatus.FAILED, 0, b"")
        with pytest.raises(ValueError, match="negative"):
            ParseOutcome(DocumentStatus.SUCCEEDED, -1, b"")
