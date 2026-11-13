from typing import Final
from xml.etree.ElementTree import Element

from ParserService.Domain.Documents.CellValue import CellValue
from ParserService.Infrastructure.Extraction.Ods.OdsAttributes import OdsAttributes
from ParserService.Infrastructure.Extraction.Ods.OdsCellReader import OdsCellReader
from ParserService.Infrastructure.Extraction.Ods.OdsMerge import OdsMerge
from ParserService.Infrastructure.Extraction.Ods.OdsName import OdsName
from ParserService.Infrastructure.Extraction.Ods.OdsSheetState import OdsSheetState


class OdsRowReader:
    """Reads one ODS row into the sheet state, with its real row and column numbers.

    Repeated rows and columns count towards the numbering but are stored only where
    they hold values. Merged cells are expanded: every cell a merged range covers
    carries its value (brief, section 2.2). Counts are capped at the OpenDocument
    maximum sheet size, so a forged repeat count cannot run away.
    """

    MAX_ROWS: Final = 1_048_576
    MAX_COLUMNS: Final = 16_384

    def __init__(self, cells: OdsCellReader, attributes: OdsAttributes) -> None:
        self._cells = cells
        self._attributes = attributes

    def read(self, row: Element, state: OdsSheetState) -> None:
        """Read a ``table:table-row`` element.

        Args:
            row: The row element, complete with its cells.
            state: The sheet being read.
        """
        maximum = max(1, self.MAX_ROWS - state.row + 1)
        repeat = self._attributes.count(row, OdsName.ROWS_REPEATED, maximum)
        column = 1
        for node in row:
            column = self._node(node, column, state)
        state.end_row(repeat)

    def _node(self, node: Element, column: int, state: OdsSheetState) -> int:
        if node.tag not in (OdsName.CELL, OdsName.COVERED_CELL):
            return column
        maximum = max(1, self.MAX_COLUMNS - column + 1)
        repeat = self._attributes.count(node, OdsName.COLUMNS_REPEATED, maximum)
        if node.tag == OdsName.COVERED_CELL:
            state.put_covered(column, repeat)
        else:
            self._value(node, (column, repeat), state)
        return column + repeat

    def _value(self, node: Element, span: tuple[int, int], state: OdsSheetState) -> None:
        column, repeat = span
        value = self._cells.read(node)
        state.put(column, value, repeat)
        state.count_formulas(repeat if isinstance(value, CellValue) else 0)
        rows = self._attributes.count(node, OdsName.ROWS_SPANNED, self.MAX_ROWS)
        columns = self._attributes.count(node, OdsName.COLUMNS_SPANNED, self.MAX_COLUMNS)
        if rows > 1 or columns > 1:
            last_row, last_column = state.row + rows - 1, column + columns - 1
            state.merge(OdsMerge(state.row, last_row, column, last_column, value))
