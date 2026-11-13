from typing import ClassVar, Literal

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
    """Durable queue backed by job rows; safe when several worker slots claim at once.

    PostgreSQL skips rows another claimer has locked (FOR UPDATE SKIP LOCKED). On top
    of that the claim only succeeds if the row is still queued when it is updated, so
    two claimers can never start the same job, on SQLite (local runs) as well; the
    loser simply tries the next job.
    """

    CLAIM_ATTEMPTS: ClassVar[int] = 20

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
        for _ in range(self.CLAIM_ATTEMPTS):
            claimed = self._policy.backoff.execute(self._claim)
            if claimed is not False:
                return claimed
        return None

    def depth(self) -> int:
        """Count queued job rows."""
        statement = select(func.count()).where(self._table.c.status == JobStatus.QUEUED.value)
        with self._engine.connect() as connection:
            return int(connection.execute(statement).scalar_one())

    def _claim(self) -> JobId | Literal[False] | None:
        # False means another claimer won this row: the caller tries the next one.
        with self._engine.begin() as connection:
            row = connection.execute(self._next_queued()).mappings().first()
            if row is None:
                return None
            job = self._mapper.from_row(row).start(self._clock.now())
            still_queued = (self._table.c.id == job.id.value) & (
                self._table.c.status == JobStatus.QUEUED.value
            )
            update_row = update(self._table).where(still_queued).values(self._mapper.to_row(job))
            won = connection.execute(update_row).rowcount == 1
            return job.id if won else False

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
