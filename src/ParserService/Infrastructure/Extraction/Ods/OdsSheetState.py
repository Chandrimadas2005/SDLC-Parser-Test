from ParserService.Infrastructure.Extraction.Ods.OdsCellReader import CellReading
from ParserService.Infrastructure.Extraction.Ods.OdsMerge import OdsMerge


class OdsSheetState:
    """What has been read of one sheet so far, while its rows stream past.

    Only non-empty cells are kept, so the long runs of empty repeated cells and rows
    that spreadsheet programs write cost nothing. Merged ranges stay active until
    their last row has been read, so the cells they cover can take their value.
    """

    def __init__(self) -> None:
        self._rows: dict[int, dict[int, CellReading]] = {}
        self._current: dict[int, CellReading] = {}
        self._merges: list[OdsMerge] = []
        self._formulas = 0
        self._row = 1

    @property
    def row(self) -> int:
        """The number of the row being read."""
        return self._row

    @property
    def formulas(self) -> int:
        """How many formula cells were read."""
        return self._formulas

    def put(self, column: int, value: CellReading, repeat: int) -> None:
        """Place a value, repeated over several columns, in the current row.

        Args:
            column: The first column it fills.
            value: The value; empty values are not kept.
            repeat: How many columns it fills.
        """
        if value not in (None, ""):
            self._current.update(dict.fromkeys(range(column, column + repeat), value))

    def put_covered(self, column: int, repeat: int) -> None:
        """Fill cells hidden by a merged range with the range's value.

        Args:
            column: The first covered column.
            repeat: How many covered columns follow.
        """
        for position in range(column, column + repeat):
            merge = next((item for item in self._merges if item.covers(self._row, position)), None)
            if merge is not None:
                self._current[position] = merge.value

    def merge(self, merge: OdsMerge) -> None:
        """Remember a merged range whose covered cells come later.

        Args:
            merge: The range and its value.
        """
        if merge.value not in (None, ""):
            self._merges.append(merge)

    def count_formulas(self, count: int) -> None:
        """Add formula cells to the sheet's count.

        Args:
            count: How many formula cells were read.
        """
        self._formulas += count

    def end_row(self, repeat: int) -> None:
        """Finish the current row, which the file may repeat several times.

        Args:
            repeat: How many consecutive rows have exactly these cells.
        """
        if self._current:
            cells = dict(self._current)
            self._rows.update(dict.fromkeys(range(self._row, self._row + repeat), cells))
        self._row += repeat
        self._current = {}
        self._merges = [merge for merge in self._merges if merge.last_row >= self._row]

    def matrix(self) -> list[list[CellReading]]:
        """The sheet as rows of values from row 1 to the last row holding a value.

        Returns:
            One list per row; empty cells are ``None``.
        """
        last = max(self._rows, default=0)
        return [self._dense(self._rows.get(number, {})) for number in range(1, last + 1)]

    @staticmethod
    def _dense(cells: dict[int, CellReading]) -> list[CellReading]:
        return [cells.get(column) for column in range(1, max(cells, default=0) + 1)]
