from typing import Protocol


class TemporaryFileCleaner(Protocol):
    """Port for removing incomplete temporary artifacts after disk pressure."""

    def clean(self) -> None:
        """Remove safe-to-delete temporary files."""
        ...
