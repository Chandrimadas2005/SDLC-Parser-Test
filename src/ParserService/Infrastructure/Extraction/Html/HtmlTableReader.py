from collections.abc import Sequence
from typing import Final

from bs4.element import Tag

from ParserService.Domain.Documents.Confidence import Confidence
from ParserService.Domain.Documents.Table import Table
from ParserService.Domain.Documents.TableRow import TableRow
from ParserService.Infrastructure.Extraction.Html.HtmlAttribute import HtmlAttribute
from ParserService.Infrastructure.Extraction.Html.HtmlTag import HtmlTag


class HtmlTableReader:
    """Reads an HTML table as data: rows and cells, merged cells expanded (brief, 2.2).

    Only the table's own rows are read; a table nested inside a cell becomes part of
    that cell's text. A cell spanning several columns or rows (``colspan`` and
    ``rowspan``) puts its value in every position it covers. A first row made only
    of ``th`` cells is the header row: its texts name the columns. Other columns are
    named ``column_1``, ``column_2`` and so on. Row numbers count the table's rows
    from one, header included.
    """

    HEADER_CONFIDENCE: Final = Confidence(0.95)
    COLUMN_PREFIX: Final = "column_"
    MAX_SPAN: Final = 1_000
    CELL_TAGS: Final = (HtmlTag.TH, HtmlTag.TD)

    def read(self, table: Tag) -> Table:
        """Read one table element.

        Args:
            table: The ``table`` element.

        Returns:
            The table as data.
        """
        rows = [row for row in table.find_all(HtmlTag.TR) if self._owner(row) is table]
        values = self._expand(rows)
        if not rows or not self._is_header(rows[0]):
            return Table(self._rows(values, (), 1))
        names = self._names(values[0])
        return Table(self._rows(values[1:], names, 2), 1, self.HEADER_CONFIDENCE)

    @staticmethod
    def _owner(row: Tag) -> Tag | None:
        return row.find_parent(HtmlTag.TABLE)

    def _expand(self, rows: Sequence[Tag]) -> list[list[str]]:
        carried: dict[int, tuple[int, str]] = {}
        return [self._row(row, carried) for row in rows]

    def _row(self, row: Tag, carried: dict[int, tuple[int, str]]) -> list[str]:
        values: list[str] = []
        for cell in row.find_all(self.CELL_TAGS, recursive=False):
            self._fill_carried(values, carried)
            self._place(cell, values, carried)
        self._fill_carried(values, carried)
        return values

    @staticmethod
    def _fill_carried(values: list[str], carried: dict[int, tuple[int, str]]) -> None:
        while len(values) in carried:
            remaining, value = carried.pop(len(values))
            if remaining > 1:
                carried[len(values)] = (remaining - 1, value)
            values.append(value)

    def _place(self, cell: Tag, values: list[str], carried: dict[int, tuple[int, str]]) -> None:
        text = " ".join(cell.get_text(" ").split())
        rows_down = self._span(cell, HtmlAttribute.ROWSPAN)
        for _ in range(self._span(cell, HtmlAttribute.COLSPAN)):
            if rows_down > 1:
                carried[len(values)] = (rows_down - 1, text)
            values.append(text)

    def _span(self, cell: Tag, attribute: HtmlAttribute) -> int:
        value = attribute.of(cell)
        return min(int(value), self.MAX_SPAN) if value.isdigit() and int(value) > 0 else 1

    @staticmethod
    def _is_header(row: Tag) -> bool:
        cells = row.find_all(HtmlTableReader.CELL_TAGS, recursive=False)
        return bool(cells) and all(cell.name == HtmlTag.TH for cell in cells)

    def _names(self, header: Sequence[str]) -> tuple[str, ...]:
        return tuple(
            name if name and header.count(name) == 1 else f"{self.COLUMN_PREFIX}{index}"
            for index, name in enumerate(header, 1)
        )

    def _rows(
        self, values: Sequence[Sequence[str]], names: Sequence[str], first: int
    ) -> tuple[TableRow, ...]:
        return tuple(
            TableRow(number, {self._name(names, index): value for index, value in enumerate(row)})
            for number, row in enumerate(values, first)
        )

    def _name(self, names: Sequence[str], index: int) -> str:
        return names[index] if index < len(names) else f"{self.COLUMN_PREFIX}{index + 1}"
