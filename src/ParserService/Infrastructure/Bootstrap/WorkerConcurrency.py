import os
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar, Final

from ParserService.Infrastructure.Config.EnvironmentReader import EnvironmentReader
from ParserService.Infrastructure.Config.EnvironmentVariable import EnvironmentVariable


class WorkerConcurrency:
    """Decides how many jobs one worker process parses at the same time.

    ``PARSER_WORKER_CONCURRENCY`` sets it explicitly. Without it, the number follows
    the memory available to the container (its cgroup limit, or the machine's RAM):
    what is left after a reserve for the worker itself, divided by the per-job memory
    limit, so concurrent jobs can never ask for more memory than exists. More
    throughput beyond that comes from running more worker containers.
    """

    CGROUP_MEMORY: ClassVar[Path] = Path("/sys/fs/cgroup/memory.max")
    RESERVED_MB: Final = 512
    MAX_SLOTS: Final = 64
    MEGABYTE: Final = 1024 * 1024

    def resolve(self, environment: Mapping[str, str], job_memory_mb: int) -> int:
        """Return the number of jobs to run at once.

        Args:
            environment: The process environment.
            job_memory_mb: The memory limit of one job.

        Returns:
            The configured value, or one derived from the available memory.

        Raises:
            ValueError: If the configured value is not a positive integer.
        """
        automatic = self.from_memory(job_memory_mb)
        slots = EnvironmentReader(environment).integer(
            EnvironmentVariable.WORKER_CONCURRENCY, automatic
        )
        if slots <= 0:
            message = f"{EnvironmentVariable.WORKER_CONCURRENCY} must be positive"
            raise ValueError(message)
        return slots

    def from_memory(self, job_memory_mb: int) -> int:
        """Derive the number of slots from the memory that is available.

        Args:
            job_memory_mb: The memory limit of one job.

        Returns:
            Between 1 and ``MAX_SLOTS``.
        """
        usable = self.available_mb() - self.RESERVED_MB
        return max(1, min(self.MAX_SLOTS, usable // job_memory_mb))

    def available_mb(self) -> int:
        """Memory available to this container, in megabytes."""
        limit = self._cgroup_limit()
        if limit is not None:
            return limit // self.MEGABYTE
        pages = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        return pages // self.MEGABYTE

    def _cgroup_limit(self) -> int | None:
        try:
            text = self.CGROUP_MEMORY.read_text(encoding="ascii").strip()
        except OSError:
            return None
        return int(text) if text.isdigit() else None
