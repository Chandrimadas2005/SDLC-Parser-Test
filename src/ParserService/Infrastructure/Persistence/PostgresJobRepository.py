from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError

from ParserService.Domain.Errors.JobRepositoryError import JobRepositoryError
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobKey import JobKey
from ParserService.Infrastructure.Persistence.JobRecordMapper import JobRecordMapper
from ParserService.Infrastructure.Persistence.JobTable import JobTable


class PostgresJobRepository:
    """JobRepository on PostgreSQL through SQLAlchemy Core.

    The same code runs on SQLite for local development: the engine factory maps the
    ``parser`` schema away. Expected failures (duplicate key, outage) become ``Result``
    errors; anything else is unexpected and propagates.
    """

    def __init__(self, engine: Engine, mapper: JobRecordMapper) -> None:
        self._engine = engine
        self._mapper = mapper
        self._table = JobTable.table

    def add(self, job: Job) -> Result[Job, JobRepositoryError]:
        """Insert a new job record.

        Args:
            job: The job to store.

        Returns:
            The job, or ``DUPLICATE_KEY`` / ``STORE_UNAVAILABLE``.
        """
        try:
            with self._engine.begin() as connection:
                connection.execute(insert(self._table).values(self._mapper.to_row(job)))
        except IntegrityError:
            return Result.err(JobRepositoryError.DUPLICATE_KEY)
        except OperationalError:
            return Result.err(JobRepositoryError.STORE_UNAVAILABLE)
        return Result.ok(job)

    def get(self, job_id: JobId) -> Job | None:
        """Load a job by identifier.

        Args:
            job_id: The job to look up.

        Returns:
            The job, or ``None``.
        """
        statement = select(self._table).where(self._table.c.id == job_id.value)
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return self._mapper.from_row(row) if row is not None else None

    def find_by_key(self, key: JobKey) -> Job | None:
        """Load the job for a file hash and parser version.

        Args:
            key: File hash plus parser version.

        Returns:
            The existing job, or ``None``.
        """
        statement = select(self._table).where(
            self._table.c.file_hash == key.file_hash.value,
            self._table.c.parser_version == key.parser_version.value,
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return self._mapper.from_row(row) if row is not None else None

    def update(self, job: Job) -> Result[Job, JobRepositoryError]:
        """Overwrite an existing job record.

        Args:
            job: The job in its new state.

        Returns:
            The job, or ``NOT_FOUND`` / ``STORE_UNAVAILABLE``.
        """
        statement = (
            update(self._table)
            .where(self._table.c.id == job.id.value)
            .values(self._mapper.to_row(job))
        )
        try:
            with self._engine.begin() as connection:
                updated = connection.execute(statement).rowcount
        except OperationalError:
            return Result.err(JobRepositoryError.STORE_UNAVAILABLE)
        if updated == 0:
            return Result.err(JobRepositoryError.NOT_FOUND)
        return Result.ok(job)

    def delete(self, job_id: JobId) -> bool:
        """Remove a job record.

        Args:
            job_id: The job to remove.

        Returns:
            ``True`` when a record was removed.
        """
        statement = delete(self._table).where(self._table.c.id == job_id.value)
        with self._engine.begin() as connection:
            return connection.execute(statement).rowcount > 0
