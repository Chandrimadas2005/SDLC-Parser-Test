from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from ParserService.Infrastructure.Persistence import JobTable, MigrationRunner


class TestMigrations:
    """Every revision runs forward and backward and leaves the schema as described."""

    @staticmethod
    def _tables(engine: Engine) -> list[str]:
        schema = None if engine.dialect.name == "sqlite" else JobTable.SCHEMA
        return inspect(engine).get_table_names(schema=schema)

    def test_upgrade_creates_the_jobs_table_and_records_the_revision(
        self, bare_engine: Engine
    ) -> None:
        runner = MigrationRunner(bare_engine)

        runner.upgrade()

        assert JobTable.NAME in self._tables(bare_engine)
        assert runner.current() == "0001_create_jobs"

    def test_downgrade_removes_everything_and_upgrade_works_again(
        self, bare_engine: Engine
    ) -> None:
        runner = MigrationRunner(bare_engine)
        runner.upgrade()

        runner.downgrade()
        assert JobTable.NAME not in self._tables(bare_engine)
        assert runner.current() is None

        runner.upgrade()
        assert JobTable.NAME in self._tables(bare_engine)

    def test_unique_key_constraint_and_queue_index_exist(self, engine: Engine) -> None:
        schema = None if engine.dialect.name == "sqlite" else JobTable.SCHEMA
        inspector = inspect(engine)

        unique = inspector.get_unique_constraints(JobTable.NAME, schema=schema)
        indexes = inspector.get_indexes(JobTable.NAME, schema=schema)

        assert any(
            sorted(constraint["column_names"]) == ["file_hash", "parser_version"]
            for constraint in unique
        )
        assert any(index["name"] == JobTable.STATUS_INDEX for index in indexes)
