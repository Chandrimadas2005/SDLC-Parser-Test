from collections.abc import Mapping
from pathlib import Path

from ParserService.Infrastructure.Config.EnvironmentVariable import EnvironmentVariable


class EnvironmentReader:
    """Typed access to environment variables, with defaults and clear errors."""

    def __init__(self, environment: Mapping[str, str]) -> None:
        self._environment = environment

    def text(self, variable: EnvironmentVariable, default: str) -> str:
        """Read a variable as text.

        Args:
            variable: Which variable to read.
            default: Used when the variable is unset or blank.

        Returns:
            The trimmed value or the default.
        """
        value = self._environment.get(variable, "").strip()
        return value or default

    def integer(self, variable: EnvironmentVariable, default: int) -> int:
        """Read a variable as an integer.

        Args:
            variable: Which variable to read.
            default: Used when the variable is unset or blank.

        Returns:
            The parsed integer or the default.

        Raises:
            ValueError: If the value is set but is not an integer.
        """
        text = self.text(variable, str(default))
        try:
            return int(text)
        except ValueError as error:
            message = f"{variable} must be an integer, got {text!r}"
            raise ValueError(message) from error

    def path(self, variable: EnvironmentVariable, default: str) -> Path:
        """Read a variable as a file system path.

        Args:
            variable: Which variable to read.
            default: Used when the variable is unset or blank.

        Returns:
            The path, not resolved and not checked for existence.
        """
        return Path(self.text(variable, default))
