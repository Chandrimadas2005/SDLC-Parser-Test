from dataclasses import replace
from pathlib import Path

from sqlalchemy.engine import Engine

from ParserService.Domain.Errors import JobQueueError
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
from ParserService.Infrastructure.Persistence import (
    DatabaseEngineFactory,
    JobRecordMapper,
    PostgresJobRepository,
)
from ParserService.Infrastructure.Queue import PostgresJobQueue
from tests.Fakes import FixedClock


class TestPostgresJobQueue:
    """Queued rows are the queue: oldest first, claimed once, started atomically."""

    @staticmethod
    def _job(index: int) -> Job:
        return Job(
            id=JobId.new(),
            key=JobKey(FileHash(f"{index:064x}"), ParserVersion("0.1.0")),
            file_name=FileName(f"file-{index}.txt"),
            file_pointer=ArtifactPointer(f"files/{index}/original.txt"),
            created_at=Instant(1_000 + index),
        )

    def test_claim_returns_oldest_first_and_starts_the_job(self, engine: Engine) -> None:
        repository = PostgresJobRepository(engine, JobRecordMapper())
        first, second = self._job(1), self._job(2)
        repository.add(second)
        repository.add(first)
        queue = PostgresJobQueue(engine, FixedClock(Instant(5_000)), capacity=10)

        assert queue.depth() == 2
        assert queue.claim() == first.id
        assert queue.claim() == second.id
        assert queue.claim() is None

        started = repository.get(first.id)
        assert started is not None
        assert started.status is JobStatus.RUNNING
        assert started.attempt_count == 1
        assert started.started_at == Instant(5_000)
        assert queue.depth() == 0

    def test_enqueue_accepts_until_the_capacity_is_exceeded(self, engine: Engine) -> None:
        repository = PostgresJobRepository(engine, JobRecordMapper())
        queue = PostgresJobQueue(engine, FixedClock(Instant(1)), capacity=2)
        results = []
        for job in (self._job(index) for index in range(3)):
            repository.add(job)
            results.append(queue.enqueue(job.id))

        assert [result.is_ok for result in results] == [True, True, False]
        assert results[2].unwrap_err() is JobQueueError.QUEUE_FULL

    def test_requeued_job_is_claimed_again(self, engine: Engine) -> None:
        repository = PostgresJobRepository(engine, JobRecordMapper())
        job = self._job(7)
        repository.add(job)
        queue = PostgresJobQueue(engine, FixedClock(Instant(2_000)), capacity=10)
        queue.claim()
        running = repository.get(job.id)
        assert running is not None
        repository.update(replace(running, status=JobStatus.QUEUED))

        assert queue.claim() == job.id
        reclaimed = repository.get(job.id)
        assert reclaimed is not None
        assert reclaimed.attempt_count == 2

    def test_unreachable_database_is_reported(self, tmp_path: Path) -> None:
        engine = DatabaseEngineFactory().create(f"sqlite:///{tmp_path.as_posix()}")
        queue = PostgresJobQueue(engine, FixedClock(Instant(1)), capacity=1)

        assert queue.enqueue(JobId.new()).unwrap_err() is JobQueueError.QUEUE_UNAVAILABLE
