from dataclasses import dataclass

from ParserService.Domain.Documents.Confidence import Confidence
from ParserService.Domain.Documents.TableRow import TableRow


@dataclass(frozen=True, slots=True)
class Table:
    """A table as data: its rows, and the header row if one was detected.

    A detected header row always comes with how confident the detection was
    (brief, section 2.2).
    """

    rows: tuple[TableRow, ...]
    header_row: int | None = None
    header_confidence: Confidence | None = None

    def __post_init__(self) -> None:
        if (self.header_row is None) != (self.header_confidence is None):
            message = "a header row and its confidence are given together"
            raise ValueError(message)
        if self.header_row is not None and self.header_row < 1:
            message = "row numbers are counted from 1"
            raise ValueError(message)
