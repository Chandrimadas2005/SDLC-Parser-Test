import os
from typing import Final

from alembic import context
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ParserService.Infrastructure.Config.EnvironmentVariable import EnvironmentVariable
from ParserService.Infrastructure.Persistence.DatabaseEngineFactory import DatabaseEngineFactory
from ParserService.Infrastructure.Persistence.JobTable import JobTable


class MigrationEnvironment:
    """What Alembic's ``env.py`` runs: configures the migration context and executes it.

    Works both in process (``MigrationRunner`` passes a connection) and from the
    ``alembic`` command line (an engine is built from ``PARSER_DATABASE_URL``).
    """

    CONNECTION_ATTRIBUTE: Final = "connection"
    CREATE_SCHEMA: Final = f"CREATE SCHEMA IF NOT EXISTS {JobTable.SCHEMA}"

    def run(self) -> None:
        """Run the migrations Alembic asked for, on the connection it was given."""
        connection = context.config.attributes.get(self.CONNECTION_ATTRIBUTE)
        if isinstance(connection, Connection):
            self._run_on(connection)
            return
        database_url = os.environ[EnvironmentVariable.DATABASE_URL]
        with DatabaseEngineFactory().create(database_url).begin() as fresh_connection:
            self._run_on(fresh_connection)

    def _run_on(self, connection: Connection) -> None:
        is_sqlite = connection.dialect.name == DatabaseEngineFactory.SQLITE
        if not is_sqlite:
            connection.execute(text(self.CREATE_SCHEMA))
        context.configure(
            connection=connection,
            target_metadata=JobTable.metadata,
            include_schemas=True,
            version_table_schema=None if is_sqlite else JobTable.SCHEMA,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()
