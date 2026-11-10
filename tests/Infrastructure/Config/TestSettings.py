from pathlib import Path

import pytest

from ParserService.Infrastructure.Config import EnvironmentVariable, Limits, Settings


class TestSettings:
    """Settings come from the environment Enum only, with documented defaults."""

    def test_defaults_apply_when_nothing_is_set(self) -> None:
        settings = Settings.from_environment({})

        assert settings.database_url == Settings.DEFAULT_DATABASE_URL
        assert settings.artifact_root == Path(Settings.DEFAULT_ARTIFACT_ROOT)
        assert settings.log_level == "INFO"
        assert settings.http_port == Settings.DEFAULT_HTTP_PORT
        assert settings.limits == Limits()

    def test_values_are_read_and_blank_values_fall_back(self) -> None:
        settings = Settings.from_environment(
            {
                EnvironmentVariable.DATABASE_URL: "postgresql+pg8000://u:p@db/parser",
                EnvironmentVariable.ARTIFACT_ROOT: "/data/artifacts",
                EnvironmentVariable.LOG_LEVEL: "debug",
                EnvironmentVariable.HTTP_PORT: " 9000 ",
                EnvironmentVariable.MAX_FILE_SIZE_BYTES: "1024",
                EnvironmentVariable.QUEUE_CAPACITY: "",
                EnvironmentVariable.RETENTION_DAYS: "7",
            }
        )

        assert settings.database_url == "postgresql+pg8000://u:p@db/parser"
        assert settings.artifact_root == Path("/data/artifacts")
        assert settings.log_level == "DEBUG"
        assert settings.http_port == 9000
        assert settings.limits.max_file_size_bytes == 1024
        assert settings.limits.queue_capacity == Limits.DEFAULT_QUEUE_CAPACITY
        assert settings.limits.retention_days == 7

    def test_non_integer_limit_is_rejected_with_the_variable_name(self) -> None:
        with pytest.raises(ValueError, match="PARSER_MAX_PAGES must be an integer"):
            Settings.from_environment({EnvironmentVariable.MAX_PAGES: "many"})

    def test_non_positive_limit_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be positive"):
            Settings.from_environment({EnvironmentVariable.MAX_ATTEMPTS: "0"})

    def test_every_variable_has_the_service_prefix(self) -> None:
        assert all(variable.value.startswith("PARSER_") for variable in EnvironmentVariable)
