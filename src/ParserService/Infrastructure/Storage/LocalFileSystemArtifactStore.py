import os
import tempfile
from pathlib import Path

from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer


class LocalFileSystemArtifactStore:
    """ArtifactStore on a local directory. Writes are atomic: temp file, then rename.

    Every pointer resolves to a path below the root; ``ArtifactPointer`` already rejects
    absolute keys and ``..`` segments, and this adapter checks the resolved path again.
    """

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, pointer: ArtifactPointer, content: bytes) -> None:
        """Store bytes under a pointer, replacing any previous content atomically.

        Args:
            pointer: Where to store the artifact.
            content: The bytes to store.
        """
        target = self._path(pointer)
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=f".tmp-{os.getpid()}-")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(target)

    def read(self, pointer: ArtifactPointer) -> bytes | None:
        """Load the bytes under a pointer.

        Args:
            pointer: The artifact to load.

        Returns:
            The stored bytes, or ``None`` when nothing is stored there.
        """
        target = self._path(pointer)
        return target.read_bytes() if target.is_file() else None

    def exists(self, pointer: ArtifactPointer) -> bool:
        """Check whether an artifact is stored under a pointer.

        Args:
            pointer: The artifact to check.

        Returns:
            ``True`` when a file exists there.
        """
        return self._path(pointer).is_file()

    def delete(self, pointer: ArtifactPointer) -> bool:
        """Remove an artifact and any directories it leaves empty.

        Args:
            pointer: The artifact to remove.

        Returns:
            ``True`` when a file was removed.
        """
        target = self._path(pointer)
        if not target.is_file():
            return False
        target.unlink()
        self._prune(target.parent)
        return True

    def _path(self, pointer: ArtifactPointer) -> Path:
        resolved = (self._root / pointer.key).resolve()
        if not resolved.is_relative_to(self._root):
            message = f"artifact key escapes the store root: {pointer.key}"
            raise ValueError(message)
        return resolved

    def _prune(self, directory: Path) -> None:
        while directory != self._root and directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
            directory = directory.parent
