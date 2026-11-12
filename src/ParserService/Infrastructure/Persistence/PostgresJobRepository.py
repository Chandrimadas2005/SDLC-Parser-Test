from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.sql import Executable

from ParserService.Domain.Errors.JobRepositoryError import JobRepositoryError
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.Instant import Instant
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobKey import JobKey
from ParserService.Domain.Jobs.JobStatus import JobStatus
from ParserService.Infrastructure.Persistence.JobRecordMapper import JobRecordMapper
from ParserService.Infrastructure.Persistence.JobTable import JobTable
from ParserService.Infrastructure.Resilience.BackoffExecutor import BackoffExecutor


class PostgresJobRepository:
    """JobRepository on PostgreSQL through SQLAlchemy Core with transient backoff."""

    def __init__(
        self, engine: Engine, mapper: JobRecordMapper, backoff: BackoffExecutor | None = None
    ) -> None:
        self._engine = engine
        self._mapper = mapper
        self._table = JobTable.table
        self._backoff = backoff or BackoffExecutor()

    def add(self, job: Job) -> Result[Job, JobRepositoryError]:
        """Insert a job, retrying transient connection failures."""
        try:
            self._backoff.execute(lambda: self._insert(job))
        except IntegrityError:
            return Result.err(JobRepositoryError.DUPLICATE_KEY)
        except (OSError, OperationalError):
            return Result.err(JobRepositoryError.STORE_UNAVAILABLE)
        return Result.ok(job)

    def get(self, job_id: JobId) -> Job | None:
        """Load a job by identifier."""
        statement = select(self._table).where(self._table.c.id == job_id.value)
        row = self._backoff.execute(lambda: self._fetch_one(statement))
        return self._mapper.from_row(row) if row is not None else None

    def find_by_key(self, key: JobKey) -> Job | None:
        """Load the job for a file hash and parser version."""
        statement = select(self._table).where(
            self._table.c.file_hash == key.file_hash.value,
            self._table.c.parser_version == key.parser_version.value,
        )
        row = self._backoff.execute(lambda: self._fetch_one(statement))
        return self._mapper.from_row(row) if row is not None else None

    def list_by_status(self, status: JobStatus) -> list[Job]:
        """List jobs in the requested state, oldest first."""
        statement = (
            select(self._table)
            .where(self._table.c.status == status.value)
            .order_by(self._table.c.created_at)
        )
        rows = self._backoff.execute(lambda: self._fetch_all(statement))
        return [self._mapper.from_row(row) for row in rows]

    def list_created_before(self, cutoff: Instant) -> list[Job]:
        """List jobs older than the retention cutoff, oldest first."""
        statement = (
            select(self._table)
            .where(self._table.c.created_at < cutoff.epoch_ms)
            .order_by(self._table.c.created_at)
        )
        rows = self._backoff.execute(lambda: self._fetch_all(statement))
        return [self._mapper.from_row(row) for row in rows]

    def update(self, job: Job) -> Result[Job, JobRepositoryError]:
        """Overwrite an existing job, retrying transient connection failures."""
        try:
            updated = self._backoff.execute(lambda: self._update(job))
        except (OSError, OperationalError):
            return Result.err(JobRepositoryError.STORE_UNAVAILABLE)
        if updated == 0:
            return Result.err(JobRepositoryError.NOT_FOUND)
        return Result.ok(job)

    def delete(self, job_id: JobId) -> bool:
        """Remove a job record."""
        statement = delete(self._table).where(self._table.c.id == job_id.value)
        return self._backoff.execute(lambda: self._delete(statement))

    def _insert(self, job: Job) -> None:
        with self._engine.begin() as connection:
            connection.execute(insert(self._table).values(self._mapper.to_row(job)))

    def _update(self, job: Job) -> int:
        statement = (
            update(self._table)
            .where(self._table.c.id == job.id.value)
            .values(self._mapper.to_row(job))
        )
        with self._engine.begin() as connection:
            return int(connection.execute(statement).rowcount or 0)

    def _fetch_one(self, statement: Executable) -> RowMapping | None:
        with self._engine.connect() as connection:
            return connection.execute(statement).mappings().first()

    def _fetch_all(self, statement: Executable) -> list[RowMapping]:
        with self._engine.connect() as connection:
            return list(connection.execute(statement).mappings().all())

    def _delete(self, statement: Executable) -> bool:
        with self._engine.begin() as connection:
            return connection.execute(statement).rowcount > 0
