from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.engine import Engine

from ParserService.Domain.Jobs import (
    ArtifactPointer,
    FileHash,
    FileName,
    Instant,
    Job,
    JobId,
    JobKey,
    ParserVersion,
)
from ParserService.Infrastructure.Persistence import JobRecordMapper, PostgresJobRepository
from ParserService.Infrastructure.Queue import PostgresJobQueue, QueuePolicy
from ParserService.Infrastructure.Resilience.BackoffExecutor import BackoffExecutor
from tests.Fakes import FixedClock


class TestConcurrentClaims:
    """Many worker slots claiming at once: every job is handed out exactly once."""

    @staticmethod
    def _job(n: int) -> Job:
        return Job(
            id=JobId.new(),
            key=JobKey(FileHash(f"{n:064x}"), ParserVersion("0.1.0")),
            file_name=FileName(f"file-{n}.txt"),
            file_pointer=ArtifactPointer(f"files/{n}/original.txt"),
            created_at=Instant(1_000 + n),
        )

    def test_parallel_claims_never_share_a_job(self, engine: Engine) -> None:
        repository = PostgresJobRepository(engine, JobRecordMapper())
        jobs = [self._job(n) for n in range(30)]
        for job in jobs:
            repository.add(job)
        policy = QueuePolicy(100, BackoffExecutor())
        queue = PostgresJobQueue(engine, FixedClock(Instant(5_000)), policy)

        with ThreadPoolExecutor(max_workers=8) as pool:
            claimed = list(pool.map(lambda _: queue.claim(), range(40)))

        taken = [job_id for job_id in claimed if job_id is not None]
        assert len(taken) == len(set(taken)) == 30
        assert set(taken) == {job.id for job in jobs}
