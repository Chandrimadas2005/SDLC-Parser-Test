from dataclasses import dataclass
from typing import Self, cast


@dataclass(frozen=True, slots=True)
class Result[T, E]:
    """Outcome of an operation that is expected to fail sometimes: a value or an error.

    Expected failures travel as ``Result`` values; exceptions are kept for the
    unexpected (brief, section 2.5 design rules). Build one with ``ok`` or ``err``.
    """

    _value: T | None
    _error: E | None
    _is_ok: bool

    @classmethod
    def ok(cls, value: T) -> Self:
        """Wrap a successful value.

        Args:
            value: The result of the operation.

        Returns:
            A successful result.
        """
        return cls(_value=value, _error=None, _is_ok=True)

    @classmethod
    def err(cls, error: E) -> Self:
        """Wrap an expected failure.

        Args:
            error: What went wrong.

        Returns:
            A failed result.
        """
        return cls(_value=None, _error=error, _is_ok=False)

    @property
    def is_ok(self) -> bool:
        """Whether the operation succeeded."""
        return self._is_ok

    @property
    def is_err(self) -> bool:
        """Whether the operation failed."""
        return not self._is_ok

    def unwrap(self) -> T:
        """Return the value of a successful result.

        Returns:
            The wrapped value.

        Raises:
            ValueError: If the result is a failure.
        """
        if not self._is_ok:
            message = f"unwrap called on a failed result: {self._error!r}"
            raise ValueError(message)
        return cast("T", self._value)

    def unwrap_err(self) -> E:
        """Return the error of a failed result.

        Returns:
            The wrapped error.

        Raises:
            ValueError: If the result is a success.
        """
        if self._is_ok:
            message = "unwrap_err called on a successful result"
            raise ValueError(message)
        return cast("E", self._error)
