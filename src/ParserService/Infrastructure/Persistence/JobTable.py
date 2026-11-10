from typing import Final

from sqlalchemy import BigInteger, Column, Index, Integer, MetaData, String, Table, UniqueConstraint

from ParserService.Infrastructure.Persistence.JobColumn import JobColumn


class JobTable:
    """SQLAlchemy Core definition of the Parser's job table, in its own schema.

    The table is created by the Alembic migrations in ``Migrations/Versions``; this
    definition is what queries are built against and what autogenerate compares to.
    """

    SCHEMA: Final = "parser"
    NAME: Final = "jobs"
    UNIQUE_KEY_CONSTRAINT: Final = "uq_jobs_file_hash_parser_version"
    STATUS_INDEX: Final = "ix_jobs_status_created_at"

    metadata = MetaData(schema=SCHEMA)
    table = Table(
        NAME,
        metadata,
        Column(JobColumn.ID, String(36), primary_key=True),
        Column(JobColumn.FILE_HASH, String(64), nullable=False),
        Column(JobColumn.PARSER_VERSION, String(64), nullable=False),
        Column(JobColumn.FILE_NAME, String(255), nullable=False),
        Column(JobColumn.STATUS, String(16), nullable=False),
        Column(JobColumn.FAILURE_REASON, String(32), nullable=True),
        Column(JobColumn.ATTEMPT_COUNT, Integer, nullable=False),
        Column(JobColumn.FILE_POINTER, String(512), nullable=False),
        Column(JobColumn.RESULT_POINTER, String(512), nullable=True),
        Column(JobColumn.WARNING_COUNT, Integer, nullable=False),
        Column(JobColumn.CREATED_AT, BigInteger, nullable=False),
        Column(JobColumn.STARTED_AT, BigInteger, nullable=True),
        Column(JobColumn.FINISHED_AT, BigInteger, nullable=True),
        Column(JobColumn.DURATION_MS, BigInteger, nullable=True),
        UniqueConstraint(JobColumn.FILE_HASH, JobColumn.PARSER_VERSION, name=UNIQUE_KEY_CONSTRAINT),
        Index(STATUS_INDEX, JobColumn.STATUS, JobColumn.CREATED_AT),
    )
