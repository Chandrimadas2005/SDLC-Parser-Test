from collections.abc import Sequence
from typing import Final

from ParserService.Domain.Documents.Confidence import Confidence
from ParserService.Domain.Documents.Table import Table
from ParserService.Domain.Documents.TableRow import TableRow


class TextTableBuilder:
    """Builds a ``Table`` from rows of cell text, as found in Word and PowerPoint tables.

    Row 1 is the header when the file marks it as one (confidence 1.0) or when its
    cells are all filled and distinct (confidence 0.7). Otherwise columns are named
    ``Column 1``, ``Column 2`` and so on.
    """

    MARKED_HEADER: Final = Confidence(1.0)
    GUESSED_HEADER: Final = Confidence(0.7)

    def build(self, rows: Sequence[Sequence[str]], *, header_marked: bool) -> Table:
        """Build a table.

        Args:
            rows: Cell text, row by row.
            header_marked: Whether the file marks row 1 as a header.

        Returns:
            The table, with its header row and confidence when one was found.
        """
        first = rows[0] if rows else ()
        names = [cell.strip() for cell in first]
        header = header_marked or (all(names) and len(set(names)) == len(names))
        keys = names if header else [f"Column {n}" for n in range(1, len(first) + 1)]
        start = 1 if header else 0
        data = tuple(
            TableRow(index + 1, self._cells(keys, row))
            for index, row in enumerate(rows)
            if index >= start
        )
        if not header:
            return Table(data)
        confidence = self.MARKED_HEADER if header_marked else self.GUESSED_HEADER
        return Table(data, header_row=1, header_confidence=confidence)

    @staticmethod
    def _cells(keys: list[str], row: Sequence[str]) -> dict[str, str]:
        width = max(len(keys), len(row))
        names = keys + [f"Column {n}" for n in range(len(keys) + 1, width + 1)]
        return {name: row[index] if index < len(row) else "" for index, name in enumerate(names)}
