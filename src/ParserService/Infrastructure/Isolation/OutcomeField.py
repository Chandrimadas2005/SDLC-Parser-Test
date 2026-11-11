from enum import StrEnum


class OutcomeField(StrEnum):
    """Field names in the worker's ``outcome.json``: counts and timings, never content."""

    STATUS = "status"
    WARNING_COUNT = "warning_count"
    ELAPSED_MS = "elapsed_ms"
    PEAK_MEMORY_KB = "peak_memory_kb"
