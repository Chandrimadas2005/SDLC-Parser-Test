from dataclasses import dataclass
from typing import Self

from ParserService.Domain.Jobs.Duration import Duration


@dataclass(frozen=True, slots=True, order=True)
class Instant:
    """A point in time as milliseconds since the Unix epoch, in UTC.

    The Domain never reads the clock; Infrastructure supplies instants through the
    ``Clock`` port, which keeps Domain and Application tests free of time mocks.
    """

    epoch_ms: int

    def __post_init__(self) -> None:
        if self.epoch_ms < 0:
            message = "an instant cannot precede the epoch"
            raise ValueError(message)

    def until(self, later: Self) -> Duration:
        """Measure the time from this instant to a later one.

        Args:
            later: The end of the interval; must not precede this instant.

        Returns:
            The elapsed duration.
        """
        return Duration(later.epoch_ms - self.epoch_ms)
