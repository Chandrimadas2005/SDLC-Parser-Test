from typing import TYPE_CHECKING, Final

from ParserService.Domain.Documents.Locator import Locator
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Infrastructure.Extraction.Ods.OdsSheetContent import OdsSheetContent
from ParserService.Infrastructure.Extraction.Ods.OdsSheetState import OdsSheetState

if TYPE_CHECKING:
    from collections.abc import Mapping


class OdsWorkbook:
    """What has been read of one workbook, sheet by sheet, while ``content.xml`` streams.

    Only sheets directly in the spreadsheet body count; a table nested inside a cell
    is ignored. When the stream breaks, the sheets read so far are kept: the sheet
    being read is reported unreadable, and the result is partial (brief, 2.5).
    """

    DEFAULT_SHEET_NAME: Final = "Sheet"

    def __init__(self) -> None:
        self.sheets: list[OdsSheetContent] = []
        self.properties: Mapping[str, str] = {}
        self._hidden_styles: set[str] = set()
        self._open: tuple[str, str, OdsSheetState] | None = None
        self._depth = 0
        self._broken = False

    @property
    def state(self) -> OdsSheetState | None:
        """The state of the sheet being read, when rows belong to a top-level sheet."""
        return self._open[2] if self._open is not None and self._depth == 1 else None

    @property
    def readable(self) -> bool:
        """Whether at least one sheet was read to its end."""
        return any(sheet.complete for sheet in self.sheets)

    @property
    def formulas(self) -> int:
        """How many formula cells the read sheets hold."""
        return sum(sheet.formulas for sheet in self.sheets)

    def enter_sheet(self, name: str, style: str) -> None:
        """Start a ``table:table`` element.

        Args:
            name: The sheet name.
            style: The sheet's table style.
        """
        self._depth += 1
        if self._depth == 1:
            fallback = f"{self.DEFAULT_SHEET_NAME}{len(self.sheets) + 1}"
            self._open = (name.strip() or fallback, style, OdsSheetState())

    def leave_sheet(self) -> None:
        """End a ``table:table`` element, keeping the sheet when it was a top-level one."""
        if self._depth == 1 and self._open is not None:
            name, style, state = self._open
            hidden = style in self._hidden_styles
            self.sheets.append(OdsSheetContent(name, hidden, state.matrix(), state.formulas))
            self._open = None
        self._depth = max(0, self._depth - 1)

    def hide_style(self, name: str) -> None:
        """Record a table style that hides its sheet.

        Args:
            name: The style name.
        """
        self._hidden_styles.add(name)

    def break_off(self) -> None:
        """Record that the content stream broke; the sheet being read is kept, empty."""
        self._broken = True
        if self._open is not None:
            name, style, _ = self._open
            hidden = style in self._hidden_styles
            self.sheets.append(OdsSheetContent(name, hidden, [], 0, complete=False))

    def unreadable(self) -> tuple[ParseWarning, ...]:
        """Warnings for what could not be read because the stream broke.

        Returns:
            One ``sheet_unreadable`` warning, for the sheet being read when the stream
            broke, or for the rest of the file; none when nothing broke.
        """
        if not self._broken:
            return ()
        locator = None if self._open is None else Locator.for_cells(self._open[0], None)
        return (ParseWarning(WarningCode.SHEET_UNREADABLE, locator),)
