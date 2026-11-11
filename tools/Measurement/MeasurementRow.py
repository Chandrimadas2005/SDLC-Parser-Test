from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MeasurementRow:
    """Parse cost of one file: its outcome, time and peak memory.

    ``outcome`` is the result status, or the failure reason when the parse failed.
    Time and memory are ``None`` when the worker reported no measurements.
    """

    file: str
    detected_type: str
    size_bytes: int
    outcome: str
    elapsed_ms: int | None
    peak_memory_kb: int | None
