from dataclasses import dataclass

from ParserService.Infrastructure.Extraction.Ods.OdsCellReader import CellReading


@dataclass(frozen=True, slots=True)
class OdsMerge:
    """A merged cell range and the value that every cell it covers carries."""

    first_row: int
    last_row: int
    first_column: int
    last_column: int
    value: CellReading

    def covers(self, row: int, column: int) -> bool:
        """Whether a position lies inside the merged range.

        Args:
            row: Row number.
            column: Column number.

        Returns:
            True when the position is covered.
        """
        rows = self.first_row <= row <= self.last_row
        return rows and self.first_column <= column <= self.last_column
