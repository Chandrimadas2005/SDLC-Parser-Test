from ParserService.Domain.Jobs import ArtifactPointer


class InMemoryArtifactStore:
    """ArtifactStore backed by a dictionary."""

    def __init__(self) -> None:
        self.artifacts: dict[ArtifactPointer, bytes] = {}

    def put(self, pointer: ArtifactPointer, content: bytes) -> None:
        """Store bytes under a pointer."""
        self.artifacts[pointer] = content

    def read(self, pointer: ArtifactPointer) -> bytes | None:
        """Load bytes stored under a pointer, or ``None``."""
        return self.artifacts.get(pointer)

    def exists(self, pointer: ArtifactPointer) -> bool:
        """Whether a pointer holds an artifact."""
        return pointer in self.artifacts

    def delete(self, pointer: ArtifactPointer) -> bool:
        """Remove an artifact; ``True`` when one existed."""
        return self.artifacts.pop(pointer, None) is not None
