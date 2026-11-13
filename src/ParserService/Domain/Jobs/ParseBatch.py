from dataclasses import dataclass

from ParserService.Domain.Jobs.BatchEntry import BatchEntry
from ParserService.Domain.Jobs.BatchId import BatchId


@dataclass(frozen=True, slots=True)
class ParseBatch:
    """Files uploaded together in one request, in upload order.

    Each file is an ordinary job (with the usual duplicate rule), so workers parse
    them in parallel; the batch only remembers which jobs belong together.
    """

    id: BatchId
    entries: tuple[BatchEntry, ...]

    def __post_init__(self) -> None:
        if not self.entries:
            message = "a batch needs at least one file"
            raise ValueError(message)
