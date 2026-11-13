import json

from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer
from ParserService.Domain.Jobs.BatchEntry import BatchEntry
from ParserService.Domain.Jobs.BatchId import BatchId
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.ParseBatch import ParseBatch
from ParserService.Domain.Ports.ArtifactStore import ArtifactStore
from ParserService.Infrastructure.Storage.BatchField import BatchField


class StoredBatchStore:
    """Keeps each batch as a small JSON document in the artifact store.

    A batch only lists its jobs, which already live in the database, so no extra
    table or migration is needed; it is written once and never changes.
    """

    FOLDER = "batches"

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    def save(self, batch: ParseBatch) -> None:
        """Store a batch.

        Args:
            batch: The batch and its jobs.
        """
        files = [
            {BatchField.FILE_NAME: entry.file_name.value, BatchField.JOB_ID: entry.job_id.value}
            for entry in batch.entries
        ]
        document = {BatchField.BATCH_ID: batch.id.value, BatchField.FILES: files}
        self._store.put(self._pointer(batch.id), json.dumps(document).encode())

    def load(self, batch_id: BatchId) -> ParseBatch | None:
        """Read a batch back.

        Args:
            batch_id: The batch to read.

        Returns:
            The batch, or ``None`` when none has this identifier.
        """
        content = self._store.read(self._pointer(batch_id))
        if content is None:
            return None
        files = json.loads(content)[BatchField.FILES]
        entries = tuple(
            BatchEntry(FileName(item[BatchField.FILE_NAME]), JobId(item[BatchField.JOB_ID]))
            for item in files
        )
        return ParseBatch(batch_id, entries)

    def _pointer(self, batch_id: BatchId) -> ArtifactPointer:
        return ArtifactPointer(f"{self.FOLDER}/{batch_id.value}.json")
