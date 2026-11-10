from ParserService.Domain.Jobs import Instant


class FixedClock:
    """A clock that returns whatever instant the test sets, so tests never mock time."""

    def __init__(self, now: Instant) -> None:
        self.current = now

    def now(self) -> Instant:
        """Read the configured instant.

        Returns:
            The instant the test set.
        """
        return self.current
