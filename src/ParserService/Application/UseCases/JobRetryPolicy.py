from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JobRetryPolicy:
    """Maximum worker attempts for a parse job."""

    max_attempts: int

    def __post_init__(self) -> None:
        """Validate the attempt limit."""
        if self.max_attempts < 1:
            message = "max attempts must be positive"
            raise ValueError(message)
