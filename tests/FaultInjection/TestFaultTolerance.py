import errno
import os
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest
from sqlalchemy.engine import Engine

from ParserService.Application.Dto.SubmitParseJobCommand import SubmitParseJobCommand
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Application.UseCases import (
    ArtifactKeys,
    DiskGuard,
    JobServices,
    ProcessNextJob,
    RecoverRunningJobs,
    SubmitParseJob,
    SubmitPolicy,
)
from ParserService.Domain.Documents import DocumentStatus, ParseOutcome
from ParserService.Domain.Errors import Result
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
from ParserService.Infrastructure.Persistence import (
    DatabaseEngineFactory,
    JobRecordMapper,
    MigrationRunner,
    PostgresJobRepository,
)
from ParserService.Infrastructure.Queue import PostgresJobQueue, QueuePolicy
from ParserService.Infrastructure.Resilience.BackoffExecutor import BackoffExecutor
from ParserService.Infrastructure.Storage.RetryingArtifactStore import RetryingArtifactStore
from tests.Fakes import (
    FakeDocumentParser,
    FixedClock,
    InMemoryArtifactStore,
    InMemoryJobQueue,
    InMemoryJobRepository,
)

KEY = JobKey(FileHash.of(b"fault-injection"), ParserVersion("0.1.0"))
JOB = Job(
    JobId.new(), KEY, FileName("synthetic.txt"), ArtifactPointer("files/fault.txt"), Instant(0)
)


_WORKER_KILL_SOURCE: Final = (
    "import os, sys; "
    "from ParserService.Infrastructure.Persistence import DatabaseEngineFactory; "
    "from ParserService.Infrastructure.Queue import PostgresJobQueue, QueuePolicy; "
    "from ParserService.Infrastructure.Time.SystemClock import SystemClock; "
    "from ParserService.Infrastructure.Resilience.BackoffExecutor import BackoffExecutor; "
    "engine = DatabaseEngineFactory().create(sys.argv[1]); "
    "queue = PostgresJobQueue(engine, SystemClock(), QueuePolicy(5, BackoffExecutor())); "
    "queue.claim(); os._exit(23)"
)


class _TransientStore(InMemoryArtifactStore):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def put(self, pointer: ArtifactPointer, content: bytes) -> None:
        self.calls += 1
        if self.calls < 3:
            raise OSError(errno.EIO, "synthetic transient I/O failure")
        super().put(pointer, content)


class _PermanentStore(InMemoryArtifactStore):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def put(self, pointer: ArtifactPointer, content: bytes) -> None:
        del pointer, content
        self.calls += 1
        raise PermissionError(errno.EACCES, "synthetic permanent I/O failure")


class _NoDisk:
    def has_room(self) -> bool:
        return False


class _TemporaryCleaner:
    def __init__(self) -> None:
        self.called = False

    def clean(self) -> None:
        self.called = True


class _WorkerCrash:
    @staticmethod
    def prepare(database_url: str) -> tuple[Engine, PostgresJobRepository]:
        engine = DatabaseEngineFactory().create(database_url)
        MigrationRunner(engine).upgrade()
        return engine, PostgresJobRepository(engine, JobRecordMapper())

    @staticmethod
    def terminate(database_url: str) -> int:
        source = _WORKER_KILL_SOURCE
        environment = os.environ.copy()
        environment["PYTHONPATH"] = (
            str(Path(__file__).parents[2] / "src") + os.pathsep + environment.get("PYTHONPATH", "")
        )
        return subprocess.run(  # noqa: S603 - fixed test script with the test database URL
            [sys.executable, "-c", source, database_url],
            env=environment,
            check=False,
            timeout=30,
        ).returncode

    @staticmethod
    def recover(database_url: str, job: Job) -> Job | None:
        engine = DatabaseEngineFactory().create(database_url)
        repository = PostgresJobRepository(engine, JobRecordMapper())
        queue = PostgresJobQueue(engine, FixedClock(Instant(20)), QueuePolicy(5, BackoffExecutor()))
        services = JobServices(
            repository, InMemoryArtifactStore(), queue, FixedClock(Instant(20)), 3
        )
        RecoverRunningJobs(services).execute()
        recovered = repository.get(job.id)
        engine.dispose()
        return recovered


class TestFaultTolerance:
    """Fault injection for the implemented fault-tolerance behaviors."""

    def test_transient_storage_failure_uses_exponential_retry(self) -> None:
        store = _TransientStore()
        retrying = RetryingArtifactStore(store, BackoffExecutor(base_delay_seconds=0))

        retrying.put(ArtifactPointer("result.json"), b"synthetic")

        assert store.calls == 3
        assert store.read(ArtifactPointer("result.json")) == b"synthetic"

    def test_permanent_storage_failure_is_not_retried(self) -> None:
        store = _PermanentStore()
        retrying = RetryingArtifactStore(store, BackoffExecutor(base_delay_seconds=0))

        with pytest.raises(PermissionError):
            retrying.put(ArtifactPointer("result.json"), b"synthetic")

        assert store.calls == 1

    def test_permanent_storage_failure_does_not_consume_retry_budget(self) -> None:
        repository, queue = InMemoryJobRepository(), InMemoryJobQueue(5)
        repository.add(JOB)
        queue.enqueue(JOB.id)
        services = JobServices(repository, _PermanentStore(), queue, FixedClock(Instant(10)), 3)
        outcome: Result[ParseOutcome, FailureReason] = Result.ok(
            ParseOutcome(DocumentStatus.SUCCEEDED, 0, b"synthetic")
        )
        use_case = ProcessNextJob(services, FakeDocumentParser(outcome), ArtifactKeys())

        use_case.execute()

        failed = repository.get(JOB.id)
        assert failed is not None
        assert failed.status is JobStatus.FAILED
        assert failed.failure_reason is FailureReason.STORAGE_PERMANENT_ERROR
        assert queue.depth() == 0

    def test_worker_timeout_is_requeued_until_attempt_budget_is_exhausted(self) -> None:
        repository, store, queue = (
            InMemoryJobRepository(),
            InMemoryArtifactStore(),
            InMemoryJobQueue(5),
        )
        repository.add(JOB)
        queue.enqueue(JOB.id)
        services = JobServices(repository, store, queue, FixedClock(Instant(10)), 1)
        use_case = ProcessNextJob(
            services, FakeDocumentParser(Result.err(FailureReason.TIMEOUT)), ArtifactKeys()
        )

        use_case.execute()

        failed = repository.get(JOB.id)
        assert failed is not None
        assert failed.status is JobStatus.FAILED
        assert failed.failure_reason is FailureReason.MAX_ATTEMPTS_EXCEEDED

    def test_low_disk_rejects_upload_and_invokes_temporary_cleanup(self) -> None:
        repository, store, queue = (
            InMemoryJobRepository(),
            InMemoryArtifactStore(),
            InMemoryJobQueue(5),
        )
        cleaner = _TemporaryCleaner()
        guard = DiskGuard(_NoDisk(), cleaner)
        services = JobServices(repository, store, queue, FixedClock(Instant(10)), 3, guard)
        use_case = SubmitParseJob(
            services, SubmitPolicy(ParserVersion("0.1.0"), 100), ArtifactKeys()
        )

        result = use_case.execute(SubmitParseJobCommand(FileName("synthetic.txt"), b"synthetic"))

        assert result.unwrap_err() is ApplicationErrorCode.DISK_FULL
        assert cleaner.called
        assert repository.jobs == {}

    def test_killed_worker_process_is_recovered_from_postgres_queue_rows(
        self, tmp_path: Path
    ) -> None:
        database_url = f"sqlite:///{(tmp_path / 'worker-crash.sqlite3').as_posix()}"
        engine, repository = _WorkerCrash.prepare(database_url)
        repository.add(JOB)
        engine.dispose()

        assert _WorkerCrash.terminate(database_url) == 23
        recovered = _WorkerCrash.recover(database_url, JOB)

        assert recovered is not None
        assert recovered.status is JobStatus.QUEUED
        assert recovered.attempt_count == 1

    def test_worker_crash_leaving_running_job_is_recovered(self) -> None:
        repository = InMemoryJobRepository()
        repository.add(JOB.start(Instant(10)))
        services = JobServices(
            repository, InMemoryArtifactStore(), InMemoryJobQueue(5), FixedClock(Instant(20)), 3
        )

        recovered_count = RecoverRunningJobs(services).execute()

        assert recovered_count == 1
        recovered = repository.get(JOB.id)
        assert recovered is not None
        assert recovered.status is JobStatus.QUEUED
