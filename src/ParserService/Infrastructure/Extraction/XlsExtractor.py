from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xlrd

from ParserService.Domain.Documents import (
    DocumentStatus,
    ExtractionRequest,
    Locator,
    ParseWarning,
    ParsedDocument,
    PropertyName,
    WarningCode,
)
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
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
        import xlrd

        try:
            workbook = xlrd.open_workbook(str(Path(request.source.location)), on_demand=True, formatting_info=True)
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
        try:
            rows = [[self._value(cell, workbook.datemode) for cell in row] for row in sheet.get_rows()]
            self._expand_merges(rows, sheet.merged_cells)
            return (sheet.name, sheet.visibility != 0, rows), None
        except (IndexError, ValueError):
            warning = ParseWarning(WarningCode.SHEET_UNREADABLE, Locator.for_cells(sheet.name, None))
            return (sheet.name, sheet.visibility != 0, []), warning
        finally:
            workbook.unload_sheet(index)

    def _value(self, cell: xlrd.sheet.Cell, datemode: int) -> object:
        if cell.ctype == self.XL_CELL_DATE:
            return self._date(float(cell.value), datemode)
        if cell.ctype == self.XL_CELL_BOOLEAN:
            return bool(cell.value)
        if cell.ctype in (self.XL_CELL_EMPTY, self.XL_CELL_BLANK):
            return None
        return cell.value

    def _date(self, serial: float, datemode: int) -> datetime:
        epoch = datetime(1904, 1, 1) if datemode else datetime(1899, 12, 30)
        return epoch + timedelta(days=serial)

    def _expand_merges(
        self, rows: list[list[object]], merged_cells: Sequence[tuple[int, int, int, int]]
    ) -> None:
        for row_start, row_end, col_start, col_end in merged_cells:
            value = rows[row_start][col_start]
            for row_index in range(row_start, row_end):
                while len(rows[row_index]) < col_end:
                    rows[row_index].append(None)
                for column_index in range(col_start, col_end):
                    rows[row_index][column_index] = value

    def _with_warnings(
        self, result: ParsedDocument, warnings: list[ParseWarning], request: ExtractionRequest
    ) -> ParsedDocument:
        if not warnings:
            return result
        combined = tuple(request.detection.warnings) + tuple(warnings) + tuple(
            warning for warning in result.warnings if warning not in request.detection.warnings
        )
        return ParsedDocument(DocumentStatus.PARTIAL, result.facts, result.elements, combined, result.outline, result.metrics)
