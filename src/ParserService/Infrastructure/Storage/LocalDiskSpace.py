import shutil
from pathlib import Path


class LocalDiskSpace:
    """Check free space on the volume containing the artifact directory."""

    def __init__(self, root: Path, minimum_free_bytes: int) -> None:
        self._root = root
        self._minimum = minimum_free_bytes

    def has_room(self) -> bool:
        """Return whether the artifact volume meets the configured free-space floor."""
        probe = self._root if self._root.exists() else self._root.parent
        return shutil.disk_usage(probe).free >= self._minimum
