import errno
import time
from collections.abc import Callable
from typing import ClassVar, TypeVar

from sqlalchemy.exc import OperationalError

T = TypeVar("T")


class BackoffExecutor:
    """Execute I/O operations with bounded exponential retry."""

    TRANSIENT_ERRNOS: ClassVar[frozenset[int]] = frozenset(
        {
            errno.EAGAIN,
            errno.EINTR,
            errno.EIO,
            errno.ECONNRESET,
            errno.ETIMEDOUT,
            errno.ECONNREFUSED,
            errno.EPIPE,
            errno.ENETDOWN,
            errno.ENETUNREACH,
        }
    )

    def __init__(self, attempts: int = 3, base_delay_seconds: float = 0.05) -> None:
        self._attempts = attempts
        self._base_delay = base_delay_seconds

    def execute(self, operation: Callable[[], T]) -> T:
        """Retry transient operating-system and database connection failures."""
        for attempt in range(self._attempts - 1):
            try:
                return operation()
            except (OSError, OperationalError) as error:
                if not self._is_transient(error):
                    raise
            time.sleep(self._base_delay * (2**attempt))
        return operation()

    @classmethod
    def _is_transient(cls, error: OSError | OperationalError) -> bool:
        if isinstance(error, OperationalError):
            return True
        return error.errno in cls.TRANSIENT_ERRNOS
