from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkerLimits:
    """Time, memory and pages a single parse may use before it is stopped (brief 2.5).

    ``max_pages`` of ``None`` means no page limit.
    """

    timeout_seconds: int
    memory_mb: int
    max_pages: int | None = None

    def __post_init__(self) -> None:
        pages = 1 if self.max_pages is None else self.max_pages
        if min(self.timeout_seconds, self.memory_mb, pages) <= 0:
            message = "worker limits must be positive"
            raise ValueError(message)
