from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer
from ParserService.Domain.Ports.ArtifactStore import ArtifactStore
from ParserService.Infrastructure.Resilience.BackoffExecutor import BackoffExecutor


class RetryingArtifactStore:
    """Apply bounded I/O backoff to every artifact-store operation."""

    def __init__(self, store: ArtifactStore, backoff: BackoffExecutor) -> None:
        self._store = store
        self._backoff = backoff

    def put(self, pointer: ArtifactPointer, content: bytes) -> None:
        """Write an artifact, retrying transient I/O failures."""
        self._backoff.execute(lambda: self._store.put(pointer, content))

    def read(self, pointer: ArtifactPointer) -> bytes | None:
        """Read an artifact, retrying transient I/O failures."""
        return self._backoff.execute(lambda: self._store.read(pointer))

    def exists(self, pointer: ArtifactPointer) -> bool:
        """Check an artifact, retrying transient I/O failures."""
        return self._backoff.execute(lambda: self._store.exists(pointer))

    def delete(self, pointer: ArtifactPointer) -> bool:
        """Delete an artifact, retrying transient I/O failures."""
        return self._backoff.execute(lambda: self._store.delete(pointer))
