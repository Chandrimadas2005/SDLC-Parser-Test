from pathlib import Path
from typing import Final

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

from ParserService.Infrastructure.Persistence.JobTable import JobTable


class DatabaseEngineFactory:
    """Builds the SQLAlchemy engine for PostgreSQL (production) or SQLite (local).

    On SQLite, which has no schemas, the ``parser`` schema is translated away so the
    same table definitions, queries and migrations run unchanged.
    """

    SQLITE: Final = "sqlite"

    def create(self, database_url: str) -> Engine:
        """Create an engine for a database URL.

        Args:
            database_url: SQLAlchemy URL, e.g. ``postgresql+pg8000://...`` or
                ``sqlite:///var/parser.sqlite3``.

        Returns:
            A ready engine with connection health checks enabled.
        """
        url = make_url(database_url)
        if url.get_backend_name() != self.SQLITE:
            return create_engine(url, pool_pre_ping=True)
        self._ensure_sqlite_directory(url.database)
        engine = create_engine(url, connect_args={"check_same_thread": False})
        return engine.execution_options(schema_translate_map={JobTable.SCHEMA: None})

    @staticmethod
    def _ensure_sqlite_directory(database: str | None) -> None:
        if database and database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
