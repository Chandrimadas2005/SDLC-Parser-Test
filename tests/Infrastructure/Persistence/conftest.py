"""Engine fixtures: a fresh SQLite file per test, and PostgreSQL when CI provides one.

Set ``PARSER_TEST_DATABASE_URL`` (e.g. ``postgresql+pg8000://parser:parser@localhost/parser``)
to run every database test against a real PostgreSQL as well. Each test starts from an
empty schema and leaves it empty again, so forward and backward migrations are
exercised on every run.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine

from ParserService.Infrastructure.Persistence import DatabaseEngineFactory, MigrationRunner

POSTGRES_URL_VARIABLE = "PARSER_TEST_DATABASE_URL"
BACKENDS = ["sqlite", "postgres"]


@pytest.fixture(params=BACKENDS)
def database_url(request: pytest.FixtureRequest, tmp_path: Path) -> str:
    if request.param == "sqlite":
        return f"sqlite:///{(tmp_path / 'parser.sqlite3').as_posix()}"
    url = os.environ.get(POSTGRES_URL_VARIABLE)
    if not url:
        pytest.skip(f"{POSTGRES_URL_VARIABLE} is not set")
    return url


@pytest.fixture
def bare_engine(database_url: str) -> Iterator[Engine]:
    engine = DatabaseEngineFactory().create(database_url)
    MigrationRunner(engine).downgrade()
    yield engine
    engine.dispose()


@pytest.fixture
def engine(bare_engine: Engine) -> Iterator[Engine]:
    runner = MigrationRunner(bare_engine)
    runner.upgrade()
    yield bare_engine
    runner.downgrade()
