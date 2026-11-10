from pathlib import Path
from typing import Final

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy.engine import Engine

from ParserService.Infrastructure.Persistence.DatabaseEngineFactory import DatabaseEngineFactory
from ParserService.Infrastructure.Persistence.JobTable import JobTable


class MigrationRunner:
    """Runs the Alembic migrations in ``Migrations/`` against an engine, in process.

    Used at service start-up (so ``docker compose up`` creates the tables) and by the
    migration tests, which run every revision forward and backward. On SQLite the
    version table lives in the default schema because SQLite has no schemas.
    """

    SCRIPT_LOCATION: Final = Path(__file__).parent / "Migrations"
    VERSION_LOCATION: Final = SCRIPT_LOCATION / "Versions"
    CONNECTION_ATTRIBUTE: Final = "connection"
    HEAD: Final = "head"
    BASE: Final = "base"

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upgrade(self, revision: str = HEAD) -> None:
        """Apply migrations up to a revision.

        Args:
            revision: Target revision; ``head`` applies everything.
        """
        with self._engine.begin() as connection:
            command.upgrade(self._config(connection), revision)

    def downgrade(self, revision: str = BASE) -> None:
        """Revert migrations down to a revision.

        Args:
            revision: Target revision; ``base`` removes every table.
        """
        with self._engine.begin() as connection:
            command.downgrade(self._config(connection), revision)

    def current(self) -> str | None:
        """Read the revision the database is at.

        Returns:
            The current revision identifier, or ``None`` when no migration has run.
        """
        with self._engine.connect() as connection:
            context = MigrationContext.configure(connection, opts=self._context_options())
            return context.get_current_revision()

    def _config(self, connection: object) -> Config:
        config = Config()
        config.set_main_option("script_location", str(self.SCRIPT_LOCATION))
        config.set_main_option("path_separator", "os")
        config.set_main_option("version_locations", str(self.VERSION_LOCATION))
        config.attributes[self.CONNECTION_ATTRIBUTE] = connection
        return config

    def _context_options(self) -> dict[str, object]:
        is_sqlite = self._engine.dialect.name == DatabaseEngineFactory.SQLITE
        return {"version_table_schema": None if is_sqlite else JobTable.SCHEMA}
