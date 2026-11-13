from typing import Protocol

from ParserService.Domain.Jobs.BatchId import BatchId
from ParserService.Domain.Jobs.ParseBatch import ParseBatch


class BatchStore(Protocol):
    """Keeps which jobs were uploaded together."""

    def save(self, batch: ParseBatch) -> None:
        """Store a batch.

        Args:
            batch: The batch and its jobs.
        """

    def load(self, batch_id: BatchId) -> ParseBatch | None:
        """Read a batch back.

        Args:
            batch_id: The batch to read.

        Returns:
            The batch, or ``None`` when no batch has this identifier.
        """
