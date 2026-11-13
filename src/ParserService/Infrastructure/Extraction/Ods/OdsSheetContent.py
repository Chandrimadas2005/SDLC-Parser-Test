from collections.abc import Sequence
from dataclasses import dataclass

from ParserService.Infrastructure.Extraction.Ods.OdsCellReader import CellReading


@dataclass(frozen=True, slots=True)
class OdsSheetContent:
    """One sheet: its name, whether it is hidden, its rows and formula count.

    ``complete`` is false for a sheet that broke off while it was read; it is kept,
    empty, so it still appears in the outline (as XLSX does), and is reported unreadable.
    """

    name: str
    hidden: bool
    rows: Sequence[Sequence[CellReading]]
    formulas: int
    complete: bool = True

    def as_builder_sheet(self) -> tuple[str, bool, Sequence[Sequence[object]]]:
        """The sheet in the form ``SpreadsheetTableBuilder`` takes.

        Returns:
            The name, the hidden flag and the rows.
        """
        return self.name, self.hidden, self.rows
