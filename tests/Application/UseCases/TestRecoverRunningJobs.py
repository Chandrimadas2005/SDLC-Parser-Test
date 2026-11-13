from ParserService.Application.UseCases import (
    GetFailedParseJobs,
    JobServices,
    RecoverRunningJobs,
    RetryParseJob,
)
from ParserService.Domain.Jobs import (
    ArtifactPointer,
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
from tests.Fakes import FixedClock, InMemoryArtifactStore, InMemoryJobQueue, InMemoryJobRepository

KEY = JobKey(FileHash.of(b"recover"), ParserVersion("0.1.0"))
JOB = Job(
    JobId.new(), KEY, FileName("recover.txt"), ArtifactPointer("files/recover.txt"), Instant(0)
)


class TestRecoverRunningJobs:
    """Startup recovery returns unfinished rows to the durable queue."""

    def test_running_job_is_requeued(self) -> None:
        repository = InMemoryJobRepository()
        repository.add(JOB.start(Instant(10)))
        services = JobServices(
            repository, InMemoryArtifactStore(), InMemoryJobQueue(5), FixedClock(Instant(20))
        )

        assert RecoverRunningJobs(services).execute() == 1
        assert repository.jobs[JOB.id].status is JobStatus.QUEUED

    def test_running_job_without_attempts_left_is_failed(self) -> None:
        repository = InMemoryJobRepository()
        repository.add(JOB.start(Instant(10)))
        services = JobServices(
            repository, InMemoryArtifactStore(), InMemoryJobQueue(5), FixedClock(Instant(20)), 1
        )

        RecoverRunningJobs(services).execute()

        recovered = repository.jobs[JOB.id]
        assert recovered.status is JobStatus.FAILED
        assert recovered.failure_reason is FailureReason.MAX_ATTEMPTS_EXCEEDED

    def test_manual_retry_resets_the_automatic_attempt_budget(self) -> None:
        repository, queue = InMemoryJobRepository(), InMemoryJobQueue(5)
        failed = JOB.start(Instant(10)).fail(FailureReason.MAX_ATTEMPTS_EXCEEDED, Instant(20))
        repository.add(failed)
        services = JobServices(
            repository, InMemoryArtifactStore(), queue, FixedClock(Instant(30)), 1
        )

        submitted = RetryParseJob(services).execute(JOB.id).unwrap()

        retried = repository.get(JOB.id)
        assert submitted.status is JobStatus.QUEUED
        assert retried is not None
        assert retried.attempt_count == 0
        assert queue.depth() == 1

    def test_failed_jobs_use_the_repository_failed_store(self) -> None:
        repository = InMemoryJobRepository()
        repository.add(JOB.fail(FailureReason.CORRUPTED_FILE, Instant(10)))

        views = GetFailedParseJobs(repository).execute()

        assert len(views) == 1
        assert views[0].job_id == JOB.id
        assert views[0].failure_reason is FailureReason.CORRUPTED_FILE
