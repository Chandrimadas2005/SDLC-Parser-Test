from typing import Protocol


class DiskSpace(Protocol):
    """Port for checking whether the artifact volume has sufficient free space."""

    def has_room(self) -> bool:
        """Return whether free space meets the configured minimum."""
        ...
