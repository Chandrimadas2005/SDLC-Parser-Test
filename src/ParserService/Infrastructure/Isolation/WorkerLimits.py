from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkerLimits:
    """Time and memory a single parse may use before it is stopped (brief, section 2.5)."""

    timeout_seconds: int
    memory_mb: int

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.memory_mb <= 0:
            message = "worker limits must be positive"
            raise ValueError(message)
