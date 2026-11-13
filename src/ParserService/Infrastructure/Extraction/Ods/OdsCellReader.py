from datetime import date, datetime
from typing import TYPE_CHECKING, Final
from xml.etree.ElementTree import Element

from ParserService.Domain.Documents.CellValue import CellValue
from ParserService.Infrastructure.Extraction.Ods.OdsAttributes import OdsAttributes
from ParserService.Infrastructure.Extraction.Ods.OdsName import OdsName
from ParserService.Infrastructure.Extraction.Ods.OdsValueType import OdsValueType

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

type CellReading = str | int | float | bool | date | datetime | CellValue | None


class OdsCellReader:
    """Reads the value of one ODS cell, typed the way the spreadsheet stored it.

    Numbers, percentages and currencies become ``int`` or ``float``, dates become
    ``date`` or ``datetime``, booleans ``bool``, times stay ISO text, and text cells
    give their paragraphs, one line each (comments are not part of the value). A
    formula cell becomes a ``CellValue`` with the formula, the displayed text and
    the value cached when the file was saved (schema 1.1); formulas are never
    calculated here. Empty cells give ``None``.
    """

    MAX_TEXT_DEPTH: Final = 32
    TRUE: Final = "true"
    BOOLEANS: Final = frozenset({"true", "false"})

    def __init__(self, attributes: OdsAttributes) -> None:
        self._attributes = attributes
        self._readers: Mapping[str, Callable[[Element], CellReading]] = {
            OdsValueType.FLOAT: self._number,
            OdsValueType.PERCENTAGE: self._number,
            OdsValueType.CURRENCY: self._number,
            OdsValueType.DATE: self._date,
            OdsValueType.TIME: self._time,
            OdsValueType.BOOLEAN: self._boolean,
        }

    def read(self, cell: Element) -> CellReading:
        """Read a cell.

        Args:
            cell: A ``table:table-cell`` element.

        Returns:
            The typed value, a ``CellValue`` for a formula cell, or ``None`` when empty.
        """
        typed = self._typed(cell)
        formula = self._attributes.text(cell, OdsName.FORMULA)
        if not formula:
            return typed
        shown = self.text(cell) or ("" if typed is None else str(self._scalar(typed)))
        return CellValue(shown, formula, self._scalar(typed))

    def text(self, cell: Element) -> str:
        """The text of a cell's own paragraphs, one line each.

        Args:
            cell: A cell element.

        Returns:
            The text, stripped.
        """
        paragraphs = [self._inline(node, 0) for node in cell if node.tag == OdsName.PARAGRAPH]
        return "\n".join(paragraphs).strip()

    def _typed(self, cell: Element) -> CellReading:
        reader = self._readers.get(self._attributes.text(cell, OdsName.VALUE_TYPE))
        typed = reader(cell) if reader is not None else None
        return typed if typed is not None else (self.text(cell) or None)

    def _number(self, cell: Element) -> CellReading:
        try:
            number = float(self._attributes.text(cell, OdsName.VALUE))
        except ValueError:
            return None
        return int(number) if number.is_integer() and abs(number) < 2**53 else number

    def _date(self, cell: Element) -> CellReading:
        value = self._attributes.text(cell, OdsName.DATE_VALUE)
        try:
            moment = datetime.fromisoformat(value)
        except ValueError:
            return None
        return moment.date() if "T" not in value else moment

    def _time(self, cell: Element) -> CellReading:
        return self._attributes.text(cell, OdsName.TIME_VALUE) or None

    def _boolean(self, cell: Element) -> CellReading:
        value = self._attributes.text(cell, OdsName.BOOLEAN_VALUE).strip().lower()
        return value == self.TRUE if value in self.BOOLEANS else None

    @staticmethod
    def _scalar(typed: CellReading) -> str | int | float | bool | None:
        if isinstance(typed, (date, datetime)):
            return typed.isoformat()
        return None if isinstance(typed, CellValue) else typed

    def _inline(self, node: Element, depth: int) -> str:
        if depth > self.MAX_TEXT_DEPTH:
            return "".join(node.itertext())
        parts = [node.text or ""]
        for child in node:
            parts.extend((self._child(child, depth + 1), child.tail or ""))
        return "".join(parts)

    def _child(self, child: Element, depth: int) -> str:
        if child.tag == OdsName.SPACES:
            return " " * self._attributes.count(child, OdsName.SPACE_COUNT, 1_000)
        if child.tag in (OdsName.TAB, OdsName.LINE_BREAK):
            return "\t" if child.tag == OdsName.TAB else "\n"
        return self._inline(child, depth)
