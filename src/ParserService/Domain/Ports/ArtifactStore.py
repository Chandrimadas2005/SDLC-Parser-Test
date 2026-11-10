from typing import Protocol

from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer


class ArtifactStore(Protocol):
    """File storage for original uploads and parse results (JSON and Markdown).

    The database keeps only pointers; the bytes live behind this port. The first
    adapter is the local file system; object storage can follow without touching
    Domain or Application.
    """

    def put(self, pointer: ArtifactPointer, content: bytes) -> None:
        """Store bytes under a pointer, replacing anything already there.

        Writing is atomic from the reader's point of view: a pointer either resolves
        to the complete new content or to the previous content, never to a partial file.

        Args:
            pointer: Where to store the artifact.
            content: The bytes to store.
        """
        ...

    def read(self, pointer: ArtifactPointer) -> bytes | None:
        """Load the bytes stored under a pointer.

        Args:
            pointer: The artifact to load.

        Returns:
            The stored bytes, or ``None`` when nothing is stored there.
        """
        ...

    def exists(self, pointer: ArtifactPointer) -> bool:
        """Check whether an artifact is stored under a pointer.

        Args:
            pointer: The artifact to check.

        Returns:
            ``True`` when the artifact exists.
        """
        ...

    def delete(self, pointer: ArtifactPointer) -> bool:
        """Remove an artifact.

        Args:
            pointer: The artifact to remove.

        Returns:
            ``True`` when something was removed, ``False`` when nothing was stored there.
        """
        ...
