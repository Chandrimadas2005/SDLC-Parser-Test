from dataclasses import dataclass

from ParserService.Application.Dto import SubmitParseJobCommand
from ParserService.Application.Errors import ApplicationErrorCode
from ParserService.Application.UseCases import (
    ArtifactKeys,
    JobServices,
    SubmitParseJob,
    SubmitPolicy,
)
from ParserService.Domain.Errors import JobQueueError, JobRepositoryError
from ParserService.Domain.Jobs import (
    ArtifactPointer,
    FileHash,
    FileName,
    Instant,
    Job,
    JobId,
    JobKey,
    JobStatus,
    ParserVersion,
)
from tests.Fakes import FixedClock, InMemoryArtifactStore, InMemoryJobQueue, InMemoryJobRepository

VERSION = ParserVersion("0.1.0")
COMMAND = SubmitParseJobCommand(FileName("notes.TXT"), b"hello world")


@dataclass(frozen=True, slots=True)
class _Harness:
    repository: InMemoryJobRepository
    store: InMemoryArtifactStore
    queue: InMemoryJobQueue
    use_case: SubmitParseJob

    @classmethod
    def build(cls, capacity: int = 10, max_size: int = 1_000) -> "_Harness":
        repository, store, queue = (
            InMemoryJobRepository(),
            InMemoryArtifactStore(),
            InMemoryJobQueue(capacity),
        )
        services = JobServices(repository, store, queue, FixedClock(Instant(5_000)))
        use_case = SubmitParseJob(services, SubmitPolicy(VERSION, max_size), ArtifactKeys())
        return cls(repository, store, queue, use_case)


class TestSubmitParseJob:
    """Submission stores the file, records the job, queues it, and is safe to repeat."""

    def test_new_file_is_stored_recorded_and_queued(self) -> None:
        harness = _Harness.build()

        submitted = harness.use_case.execute(COMMAND).unwrap()

        job = harness.repository.get(submitted.job_id)
        assert job is not None
        assert submitted.status is JobStatus.QUEUED
        assert not submitted.already_existed
        assert job.key.file_hash == FileHash.of(b"hello world")
        assert job.created_at == Instant(5_000)
        assert job.file_pointer == ArtifactPointer(
            f"files/{job.key.file_hash.value[:2]}/{job.key.file_hash}/original.txt"
        )
        assert harness.store.read(job.file_pointer) == b"hello world"
        assert list(harness.queue.items) == [submitted.job_id]

    def test_same_bytes_and_version_return_the_existing_job(self) -> None:
        harness = _Harness.build()
        first = harness.use_case.execute(COMMAND).unwrap()

        second = harness.use_case.execute(
            SubmitParseJobCommand(FileName("renamed.txt"), b"hello world")
        ).unwrap()

        assert second.job_id == first.job_id
        assert second.already_existed
        assert len(harness.repository.jobs) == 1
        assert harness.queue.depth() == 1

    def test_file_over_the_limit_is_rejected_before_anything_is_stored(self) -> None:
        harness = _Harness.build(max_size=5)

        result = harness.use_case.execute(COMMAND)

        assert result.unwrap_err() is ApplicationErrorCode.FILE_TOO_LARGE
        assert harness.repository.jobs == {}
        assert harness.store.artifacts == {}

    def test_full_queue_rolls_back_the_record_and_the_file(self) -> None:
        harness = _Harness.build(capacity=0)

        result = harness.use_case.execute(COMMAND)

        assert result.unwrap_err() is ApplicationErrorCode.QUEUE_FULL
        assert harness.repository.jobs == {}
        assert harness.store.artifacts == {}

    def test_unavailable_queue_is_reported_as_storage_unavailable(self) -> None:
        harness = _Harness.build()
        harness.queue.failure = JobQueueError.QUEUE_UNAVAILABLE

        assert harness.use_case.execute(COMMAND).unwrap_err() is (
            ApplicationErrorCode.STORAGE_UNAVAILABLE
        )
        assert harness.repository.jobs == {}

    def test_duplicate_key_race_returns_the_job_that_won(self) -> None:
        harness = _Harness.build()
        key = JobKey(FileHash.of(COMMAND.content), VERSION)
        racer = Job(JobId.new(), key, COMMAND.file_name, ArtifactPointer("files/x"), Instant(1))
        harness.repository.racer = racer

        submitted = harness.use_case.execute(COMMAND).unwrap()

        assert submitted.job_id == racer.id
        assert submitted.already_existed

    def test_duplicate_key_without_a_visible_winner_is_a_storage_error(self) -> None:
        harness = _Harness.build()
        harness.repository.failure = JobRepositoryError.DUPLICATE_KEY

        result = harness.use_case.execute(COMMAND)

        assert result.unwrap_err() is ApplicationErrorCode.STORAGE_UNAVAILABLE

    def test_repository_outage_is_reported(self) -> None:
        harness = _Harness.build()
        harness.repository.failure = JobRepositoryError.STORE_UNAVAILABLE

        result = harness.use_case.execute(COMMAND)

        assert result.unwrap_err() is ApplicationErrorCode.STORAGE_UNAVAILABLE
