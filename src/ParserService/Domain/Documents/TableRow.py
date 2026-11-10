from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TableRow:
    """One data row of a table: its row number in the source and its cells.

    Cells are keyed by column name: the header text when a header row was found,
    otherwise the column's own name (such as ``A`` in a spreadsheet). Merged cells
    are expanded, so every cell they cover carries the value (brief, section 2.2).
    """

    row: int
    cells: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.row < 1:
            message = "row numbers are counted from 1"
            raise ValueError(message)
