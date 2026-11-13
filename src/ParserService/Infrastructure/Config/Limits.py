from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Limits:
    """Every limit the brief says must be a setting (section 2.5 design rules).

    The class constants are the proposed defaults for the Phase 0 review. They are
    deliberately conservative; the measurement script results will tune them.
    """

    DEFAULT_MAX_FILE_SIZE_BYTES: ClassVar[int] = 100 * 1024 * 1024
    DEFAULT_MAX_PAGES: ClassVar[int] = 2_000
    DEFAULT_JOB_TIMEOUT_SECONDS: ClassVar[int] = 300
    DEFAULT_JOB_MEMORY_LIMIT_MB: ClassVar[int] = 2_048
    DEFAULT_ARCHIVE_MAX_DEPTH: ClassVar[int] = 3
    DEFAULT_ARCHIVE_MAX_FILES: ClassVar[int] = 1_000
    DEFAULT_ARCHIVE_MAX_EXPANDED_BYTES: ClassVar[int] = 1024 * 1024 * 1024
    DEFAULT_MAX_ATTEMPTS: ClassVar[int] = 3
    DEFAULT_QUEUE_CAPACITY: ClassVar[int] = 500
    DEFAULT_RETENTION_DAYS: ClassVar[int] = 30
    DEFAULT_MIN_FREE_DISK_BYTES: ClassVar[int] = 2 * 1024 * 1024 * 1024
    DEFAULT_MAX_BATCH_FILES: ClassVar[int] = 20

    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES
    max_pages: int = DEFAULT_MAX_PAGES
    job_timeout_seconds: int = DEFAULT_JOB_TIMEOUT_SECONDS
    job_memory_limit_mb: int = DEFAULT_JOB_MEMORY_LIMIT_MB
    archive_max_depth: int = DEFAULT_ARCHIVE_MAX_DEPTH
    archive_max_files: int = DEFAULT_ARCHIVE_MAX_FILES
    archive_max_expanded_bytes: int = DEFAULT_ARCHIVE_MAX_EXPANDED_BYTES
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    queue_capacity: int = DEFAULT_QUEUE_CAPACITY
    retention_days: int = DEFAULT_RETENTION_DAYS
    min_free_disk_bytes: int = DEFAULT_MIN_FREE_DISK_BYTES
    max_batch_files: int = DEFAULT_MAX_BATCH_FILES

    def __post_init__(self) -> None:
        for name in self.__slots__:
            if getattr(self, name) <= 0:
                message = f"limit {name} must be positive"
                raise ValueError(message)
