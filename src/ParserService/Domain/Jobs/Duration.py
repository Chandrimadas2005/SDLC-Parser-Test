from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class Duration:
    """A non-negative span of time in whole milliseconds."""

    milliseconds: int

    def __post_init__(self) -> None:
        if self.milliseconds < 0:
            message = "a duration cannot be negative"
            raise ValueError(message)
