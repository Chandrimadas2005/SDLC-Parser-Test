"""Create the parser.jobs table.

Revision ID: 0001_create_jobs
Revises: none
"""

from typing import Final

import sqlalchemy as sa
from alembic import op

revision: Final = "0001_create_jobs"
down_revision: Final = None
branch_labels: Final = None
depends_on: Final = None


class CreateJobsTable:
    """First migration: the job record table with its unique file-hash plus version rule.

    Column definitions are spelled out here on purpose. A migration is a snapshot and
    must not change when ``JobTable`` changes later.
    """

    SCHEMA: Final = "parser"
    TABLE: Final = "jobs"

    def upgrade(self) -> None:
        """Create the table, its unique constraint and the queue index."""
        op.create_table(
            self.TABLE,
            *self._columns(),
            sa.UniqueConstraint(
                "file_hash", "parser_version", name="uq_jobs_file_hash_parser_version"
            ),
            schema=self.SCHEMA,
        )
        op.create_index(
            "ix_jobs_status_created_at",
            self.TABLE,
            ["status", "created_at"],
            schema=self.SCHEMA,
        )

    @staticmethod
    def _columns() -> list[sa.Column[object]]:
        return [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("file_hash", sa.String(64), nullable=False),
            sa.Column("parser_version", sa.String(64), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("failure_reason", sa.String(32), nullable=True),
            sa.Column("attempt_count", sa.Integer, nullable=False),
            sa.Column("file_pointer", sa.String(512), nullable=False),
            sa.Column("result_pointer", sa.String(512), nullable=True),
            sa.Column("warning_count", sa.Integer, nullable=False),
            sa.Column("created_at", sa.BigInteger, nullable=False),
            sa.Column("started_at", sa.BigInteger, nullable=True),
            sa.Column("finished_at", sa.BigInteger, nullable=True),
            sa.Column("duration_ms", sa.BigInteger, nullable=True),
        ]

    def downgrade(self) -> None:
        """Drop the index and the table."""
        op.drop_index("ix_jobs_status_created_at", table_name=self.TABLE, schema=self.SCHEMA)
        op.drop_table(self.TABLE, schema=self.SCHEMA)


upgrade = CreateJobsTable().upgrade
downgrade = CreateJobsTable().downgrade
