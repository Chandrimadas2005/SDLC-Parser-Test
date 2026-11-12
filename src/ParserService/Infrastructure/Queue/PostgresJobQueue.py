from sqlalchemy import func, select, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import Executable

from ParserService.Domain.Errors.JobQueueError import JobQueueError
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobStatus import JobStatus
from ParserService.Domain.Ports.Clock import Clock
from ParserService.Infrastructure.Persistence.JobRecordMapper import JobRecordMapper
from ParserService.Infrastructure.Persistence.JobTable import JobTable
from ParserService.Infrastructure.Queue.QueuePolicy import QueuePolicy


class PostgresJobQueue:
    """Durable queue backed by job rows and claimed with FOR UPDATE SKIP LOCKED."""

    def __init__(self, engine: Engine, clock: Clock, policy: QueuePolicy) -> None:
        self._engine = engine
        self._clock = clock
        self._policy = policy
        self._mapper = JobRecordMapper()
        self._table = JobTable.table

    def enqueue(self, job_id: JobId) -> Result[JobId, JobQueueError]:
        """Accept an already-persisted queued job unless the queue is full."""
        try:
            depth = self._policy.backoff.execute(self.depth)
        except (OSError, OperationalError):
            return Result.err(JobQueueError.QUEUE_UNAVAILABLE)
        if depth > self._policy.capacity:
            return Result.err(JobQueueError.QUEUE_FULL)
        return Result.ok(job_id)

    def claim(self) -> JobId | None:
        """Atomically take the oldest queued job and mark it running."""
        return self._policy.backoff.execute(self._claim)

    def depth(self) -> int:
        """Count queued job rows."""
        statement = select(func.count()).where(self._table.c.status == JobStatus.QUEUED.value)
        with self._engine.connect() as connection:
            return int(connection.execute(statement).scalar_one())

    def _claim(self) -> JobId | None:
        with self._engine.begin() as connection:
            row = connection.execute(self._next_queued()).mappings().first()
            if row is None:
                return None
            job = self._mapper.from_row(row).start(self._clock.now())
            self._store(connection, job.id, self._mapper.to_row(job))
            return job.id

    def _next_queued(self) -> Executable:
        return (
            select(self._table)
            .where(self._table.c.status == JobStatus.QUEUED.value)
            .order_by(self._table.c.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )

    def _store(self, connection: Connection, job_id: JobId, row: dict[str, object]) -> None:
        connection.execute(update(self._table).where(self._table.c.id == job_id.value).values(row))
