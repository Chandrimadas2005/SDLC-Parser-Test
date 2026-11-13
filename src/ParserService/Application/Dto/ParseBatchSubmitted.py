from dataclasses import dataclass

from ParserService.Application.Dto.BatchFileOutcome import BatchFileOutcome
from ParserService.Domain.Jobs.BatchId import BatchId


@dataclass(frozen=True, slots=True)
class ParseBatchSubmitted:
    """Answer to a multi-file upload: the batch to poll and each file's outcome."""

    batch_id: BatchId
    files: tuple[BatchFileOutcome, ...]
