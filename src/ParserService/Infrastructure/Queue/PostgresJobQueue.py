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


class PostgresJobQueue:
    """JobQueue on the jobs table itself: queued rows are the queue (Phase 0 proposal).

    ``claim`` selects the oldest queued row with ``FOR UPDATE SKIP LOCKED``, so several
    workers never take the same job, and starts the job in the same transaction. A
    restart loses nothing: unfinished jobs are still rows and return to the queue.
    """

    def __init__(self, engine: Engine, clock: Clock, capacity: int) -> None:
        self._engine = engine
        self._clock = clock
        self._capacity = capacity
        self._mapper = JobRecordMapper()
        self._table = JobTable.table

    def enqueue(self, job_id: JobId) -> Result[JobId, JobQueueError]:
        """Accept a job whose record is already queued, unless the queue is full.

        Args:
            job_id: The job whose record was just inserted with status ``queued``.

        Returns:
            The job identifier, or ``QUEUE_FULL`` / ``QUEUE_UNAVAILABLE``.
        """
        try:
            depth = self.depth()
        except OperationalError:
            return Result.err(JobQueueError.QUEUE_UNAVAILABLE)
        if depth > self._capacity:
            return Result.err(JobQueueError.QUEUE_FULL)
        return Result.ok(job_id)

    def claim(self) -> JobId | None:
        """Atomically take the oldest queued job and mark it running.

        Returns:
            The claimed job identifier, or ``None`` when nothing is queued.
        """
        with self._engine.begin() as connection:
            row = connection.execute(self._next_queued()).mappings().first()
            if row is None:
                return None
            job = self._mapper.from_row(row).start(self._clock.now())
            self._store(connection, job.id, self._mapper.to_row(job))
            return job.id

    def depth(self) -> int:
        """Count queued jobs.

        Returns:
            The number of rows with status ``queued``.
        """
        statement = select(func.count()).where(self._table.c.status == JobStatus.QUEUED.value)
        with self._engine.connect() as connection:
            return int(connection.execute(statement).scalar_one())

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
