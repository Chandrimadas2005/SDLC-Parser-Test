from typing import Protocol

from ParserService.Domain.Jobs.Instant import Instant


class Clock(Protocol):
    """Source of the current time. Injected so Domain and Application never read a clock."""

    def now(self) -> Instant:
        """Read the current time.

        Returns:
            The current instant in UTC.
        """
        ...
