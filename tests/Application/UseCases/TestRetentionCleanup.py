from ParserService.Application.UseCases import ArtifactKeys, JobServices, RetentionCleanup
from ParserService.Domain.Jobs import (
    ArtifactPointer,
    FileHash,
    FileName,
    Instant,
    Job,
    JobCompletion,
    JobId,
    JobKey,
    JobStatus,
    ParserVersion,
)
from tests.Fakes import FixedClock, InMemoryArtifactStore, InMemoryJobQueue, InMemoryJobRepository

KEY = JobKey(FileHash.of(b"expired"), ParserVersion("0.1.0"))
FILE = ArtifactPointer("files/expired.txt")
RESULT = ArtifactPointer("results/expired.json")
JOB = Job(JobId.new(), KEY, FileName("expired.txt"), FILE, Instant(1))


class TestRetentionCleanup:
    """Expired records and all their artifacts are removed together."""

    def test_expired_job_and_artifacts_are_removed(self) -> None:
        repository, store = InMemoryJobRepository(), InMemoryArtifactStore()
        job = JOB.start(Instant(1)).complete(
            JobCompletion(JobStatus.SUCCEEDED, RESULT, 0), Instant(2)
        )
        repository.add(job)
        store.put(FILE, b"synthetic source")
        store.put(RESULT, b"synthetic result")
        keys = ArtifactKeys()
        markdown = keys.result_markdown(KEY.file_hash, KEY.parser_version)
        store.put(markdown, b"synthetic markdown")
        services = JobServices(
            repository, store, InMemoryJobQueue(5), FixedClock(Instant(3_000_000_000))
        )

        deleted = RetentionCleanup(services, keys, retention_days=1).execute()

        assert deleted == 1
        assert repository.get(job.id) is None
        assert store.artifacts == {}

    def test_recent_job_is_retained(self) -> None:
        repository, store = InMemoryJobRepository(), InMemoryArtifactStore()
        repository.add(JOB)
        services = JobServices(repository, store, InMemoryJobQueue(5), FixedClock(Instant(100)))

        assert RetentionCleanup(services, ArtifactKeys(), retention_days=30).execute() == 0
        assert repository.get(JOB.id) is not None
