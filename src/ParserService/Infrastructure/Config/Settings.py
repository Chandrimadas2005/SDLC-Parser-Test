from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Self

from ParserService.Infrastructure.Config.EnvironmentReader import EnvironmentReader
from ParserService.Infrastructure.Config.EnvironmentVariable import EnvironmentVariable
from ParserService.Infrastructure.Config.Limits import Limits


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration, read once from the environment at start-up."""

    DEFAULT_DATABASE_URL: ClassVar[str] = "sqlite:///var/parser.sqlite3"
    DEFAULT_ARTIFACT_ROOT: ClassVar[str] = "var/artifacts"
    DEFAULT_LOG_LEVEL: ClassVar[str] = "INFO"
    DEFAULT_HTTP_HOST: ClassVar[str] = "0.0.0.0"  # noqa: S104 - the container binds every interface
    DEFAULT_HTTP_PORT: ClassVar[int] = 8000

    database_url: str
    artifact_root: Path
    log_level: str
    http_host: str
    http_port: int
    limits: Limits

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> Self:
        """Build settings from environment variables, falling back to the defaults.

        Args:
            environment: Usually ``os.environ``; tests pass a plain dictionary.

        Returns:
            The parsed settings.

        Raises:
            ValueError: If a numeric variable is set to a non-integer or non-positive value.
        """
        reader = EnvironmentReader(environment)
        return cls(
            database_url=reader.text(EnvironmentVariable.DATABASE_URL, cls.DEFAULT_DATABASE_URL),
            artifact_root=reader.path(EnvironmentVariable.ARTIFACT_ROOT, cls.DEFAULT_ARTIFACT_ROOT),
            log_level=reader.text(EnvironmentVariable.LOG_LEVEL, cls.DEFAULT_LOG_LEVEL).upper(),
            http_host=reader.text(EnvironmentVariable.HTTP_HOST, cls.DEFAULT_HTTP_HOST),
            http_port=reader.integer(EnvironmentVariable.HTTP_PORT, cls.DEFAULT_HTTP_PORT),
            limits=cls._limits(reader),
        )

    LIMIT_VARIABLES: ClassVar[Mapping[str, EnvironmentVariable]] = {
        "max_file_size_bytes": EnvironmentVariable.MAX_FILE_SIZE_BYTES,
        "max_pages": EnvironmentVariable.MAX_PAGES,
        "job_timeout_seconds": EnvironmentVariable.JOB_TIMEOUT_SECONDS,
        "job_memory_limit_mb": EnvironmentVariable.JOB_MEMORY_LIMIT_MB,
        "archive_max_depth": EnvironmentVariable.ARCHIVE_MAX_DEPTH,
        "archive_max_files": EnvironmentVariable.ARCHIVE_MAX_FILES,
        "archive_max_expanded_bytes": EnvironmentVariable.ARCHIVE_MAX_EXPANDED_BYTES,
        "max_attempts": EnvironmentVariable.MAX_ATTEMPTS,
        "queue_capacity": EnvironmentVariable.QUEUE_CAPACITY,
        "retention_days": EnvironmentVariable.RETENTION_DAYS,
        "min_free_disk_bytes": EnvironmentVariable.MIN_FREE_DISK_BYTES,
        "max_batch_files": EnvironmentVariable.MAX_BATCH_FILES,
    }

    @classmethod
    def _limits(cls, reader: EnvironmentReader) -> Limits:
        defaults = Limits()
        values = {
            field: reader.integer(variable, getattr(defaults, field))
            for field, variable in cls.LIMIT_VARIABLES.items()
        }
        return Limits(**values)
