from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SyntheticPdf:
    """A generated PDF and the words each of its pages is known to contain."""

    path: Path
    expected_pages: tuple[tuple[str, ...], ...]

    @property
    def page_count(self) -> int:
        """How many pages the PDF has."""
        return len(self.expected_pages)
