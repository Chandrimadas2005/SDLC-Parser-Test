from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import xlrd

    from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import (
        SpreadsheetTableBuilder,
    )

from ParserService.Domain.Documents import (
    DocumentStatus,
    ExtractionRequest,
    Locator,
    ParsedDocument,
    ParseWarning,
    PropertyName,
    WarningCode,
)
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.XlsPropertyReader import XlsPropertyReader


class XlsExtractor:
    """Extract legacy BIFF workbooks with xlrd's on-demand worksheet loading."""

    XL_CELL_EMPTY = 0
    XL_CELL_DATE = 3
    XL_CELL_BOOLEAN = 4
    XL_CELL_BLANK = 6

    def __init__(
        self, builder: SpreadsheetTableBuilder, summary: XlsPropertyReader | None = None
    ) -> None:
        self._builder = builder
        self._summary = summary or XlsPropertyReader()

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Read legacy worksheets, opening one sheet at a time."""
        import xlrd  # noqa: PLC0415 - loaded on use so tests can substitute a fake xlrd

        try:
            workbook = xlrd.open_workbook(
                str(Path(request.source.location)), on_demand=True, formatting_info=True
            )
            sheets, warnings = self._sheets(workbook)
            request = request.with_properties(self._properties(workbook))
            workbook.release_resources()
        except (OSError, xlrd.XLRDError, ValueError):
            return Result.err(FailureReason.CORRUPTED_FILE)
        request = request.with_properties(self._summary.read(Path(request.source.location)))
        result = self._builder.build(request, sheets, 0)
        return Result.ok(self._with_warnings(result, warnings, request))

    @staticmethod
    def _properties(workbook: xlrd.book.Book) -> dict[str, str]:
        # What xlrd itself exposes; title, author and dates come from XlsPropertyReader.
        codepage = workbook.codepage
        return {
            PropertyName.LAST_MODIFIED_BY: str(workbook.user_name or "").strip(),
            PropertyName.CODEPAGE: "" if codepage is None else str(codepage),
            PropertyName.BIFF_VERSION: str(workbook.biff_version),
        }

    def _sheets(
        self, workbook: xlrd.book.Book
    ) -> tuple[list[tuple[str, bool, list[list[object]]]], list[ParseWarning]]:
        sheets: list[tuple[str, bool, list[list[object]]]] = []
        warnings: list[ParseWarning] = []
        for index in range(workbook.nsheets):
            sheet, warning = self._sheet(workbook, index)
            sheets.append(sheet)
            if warning is not None:
                warnings.append(warning)
        return sheets, warnings

    def _sheet(
        self, workbook: xlrd.book.Book, index: int
    ) -> tuple[tuple[str, bool, list[list[object]]], ParseWarning | None]:
        sheet = workbook.sheet_by_index(index)
        hidden = sheet.visibility != 0
        try:
            rows = [
                [self._value(cell, workbook.datemode) for cell in row] for row in sheet.get_rows()
            ]
            self._expand_merges(rows, sheet.merged_cells)
        except (IndexError, ValueError):
            warning = ParseWarning(
                WarningCode.SHEET_UNREADABLE, Locator.for_cells(sheet.name, None)
            )
            return (sheet.name, hidden, []), warning
        finally:
            workbook.unload_sheet(index)
        return (sheet.name, hidden, rows), None

    def _value(self, cell: xlrd.sheet.Cell, datemode: int) -> object:
        if cell.ctype == self.XL_CELL_DATE:
            return self._date(float(cell.value), datemode)
        if cell.ctype == self.XL_CELL_BOOLEAN:
            return bool(cell.value)
        if cell.ctype in (self.XL_CELL_EMPTY, self.XL_CELL_BLANK):
            return None
        return cell.value

    def _date(self, serial: float, datemode: int) -> datetime:
        # Excel dates have no time zone; compute in UTC and drop it again.
        epoch = datetime(1904, 1, 1, tzinfo=UTC) if datemode else datetime(1899, 12, 30, tzinfo=UTC)
        return (epoch + timedelta(days=serial)).replace(tzinfo=None)

    def _expand_merges(
        self, rows: list[list[object]], merged_cells: Sequence[tuple[int, int, int, int]]
    ) -> None:
        for merged in merged_cells:
            self._fill_range(rows, merged)

    @staticmethod
    def _fill_range(rows: list[list[object]], merged: tuple[int, int, int, int]) -> None:
        row_start, row_end, col_start, col_end = merged
        value = rows[row_start][col_start]
        for row in rows[row_start:row_end]:
            row.extend([None] * (col_end - len(row)))
            row[col_start:col_end] = [value] * (col_end - col_start)

    def _with_warnings(
        self, result: ParsedDocument, warnings: list[ParseWarning], request: ExtractionRequest
    ) -> ParsedDocument:
        if not warnings:
            return result
        combined = (
            tuple(request.detection.warnings)
            + tuple(warnings)
            + tuple(
                warning for warning in result.warnings if warning not in request.detection.warnings
            )
        )
        return ParsedDocument(
            DocumentStatus.PARTIAL,
            result.facts,
            result.elements,
            combined,
            result.outline,
            result.metrics,
        )
