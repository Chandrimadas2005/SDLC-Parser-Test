from dataclasses import dataclass

from ParserService.Domain.Documents.ParseOutcome import ParseOutcome


@dataclass(frozen=True, slots=True)
class WorkerResult:
    """A parse that finished inside its worker, with what it cost."""

    outcome: ParseOutcome
    elapsed_ms: int
    peak_memory_kb: int
