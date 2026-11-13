from collections.abc import Callable, Mapping
from typing import IO, Final
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from ParserService.Infrastructure.Extraction.Ods.OdsAttributes import OdsAttributes
from ParserService.Infrastructure.Extraction.Ods.OdsName import OdsName
from ParserService.Infrastructure.Extraction.Ods.OdsRowReader import OdsRowReader
from ParserService.Infrastructure.Extraction.Ods.OdsWorkbook import OdsWorkbook

type EventHandler = Callable[[Element, OdsWorkbook], bool]


class OdsContentReader:
    """Streams an ODS ``content.xml`` row by row, so memory stays flat (brief, 2.2).

    The XML is parsed with defusedxml, which refuses entity tricks and external
    references (brief, 2.6). Each row is handed to the row reader as soon as it is
    complete and then dropped from the tree, as is each finished sheet and style.
    Hidden-sheet styles come before the sheets in the file, so they are known by the
    time each sheet ends.
    """

    START: Final = "start"
    END: Final = "end"
    TABLE_FAMILY: Final = "table"
    HIDDEN: Final = "false"

    def __init__(self, rows: OdsRowReader, attributes: OdsAttributes) -> None:
        self._rows = rows
        self._attributes = attributes
        self._handlers: Mapping[tuple[str, str], EventHandler] = {
            (self.START, OdsName.SHEET): self._enter_sheet,
            (self.END, OdsName.ROW): self._row,
            (self.END, OdsName.SHEET): self._leave_sheet,
            (self.END, OdsName.STYLE_ELEMENT): self._style,
        }

    def read(self, stream: IO[bytes], workbook: OdsWorkbook) -> None:
        """Read every sheet of a content stream into a workbook.

        Args:
            stream: The ``content.xml`` stream.
            workbook: Where the sheets go.

        Raises:
            ElementTree.ParseError: When the XML is broken; sheets read so far stay.
        """
        open_elements: list[Element] = []
        for event, node in ElementTree.iterparse(stream, events=(self.START, self.END)):
            if event == self.START:
                open_elements.append(node)
            else:
                open_elements.pop()
            handler = self._handlers.get((event, node.tag))
            if handler is not None and handler(node, workbook) and open_elements:
                open_elements[-1].remove(node)

    def _enter_sheet(self, node: Element, workbook: OdsWorkbook) -> bool:
        name = self._attributes.text(node, OdsName.SHEET_NAME)
        workbook.enter_sheet(name, self._attributes.text(node, OdsName.SHEET_STYLE))
        return False

    def _row(self, node: Element, workbook: OdsWorkbook) -> bool:
        state = workbook.state
        if state is None:
            return False
        self._rows.read(node, state)
        return True

    def _leave_sheet(self, _node: Element, workbook: OdsWorkbook) -> bool:
        workbook.leave_sheet()
        return workbook.state is None

    def _style(self, node: Element, workbook: OdsWorkbook) -> bool:
        if self._attributes.text(node, OdsName.STYLE_FAMILY) == self.TABLE_FAMILY and any(
            self._attributes.text(item, OdsName.DISPLAY) == self.HIDDEN
            for item in node.iter(OdsName.TABLE_PROPERTIES)
        ):
            workbook.hide_style(self._attributes.text(node, OdsName.STYLE_NAME))
        return True
