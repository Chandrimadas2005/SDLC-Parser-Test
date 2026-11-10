"""Alembic entry point. All logic lives in MigrationEnvironment so it is typed and tested."""

from ParserService.Infrastructure.Persistence.MigrationEnvironment import MigrationEnvironment

MigrationEnvironment().run()
