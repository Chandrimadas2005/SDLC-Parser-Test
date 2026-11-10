import time

from ParserService.Domain.Jobs.Instant import Instant


class SystemClock:
    """The real wall clock, in UTC milliseconds."""

    def now(self) -> Instant:
        """Read the system time.

        Returns:
            The current instant.
        """
        return Instant(time.time_ns() // 1_000_000)
