from collections.abc import Sequence
from pathlib import Path
from xml.etree import ElementTree
import posixpath
import zipfile

from openpyxl import load_workbook
from openpyxl.cell.read_only import ReadOnlyCell
from openpyxl.workbook import Workbook
from openpyxl.utils.cell import range_boundaries
from openpyxl.worksheet._read_only import ReadOnlyWorksheet
from openpyxl.worksheet.worksheet import Worksheet

from ParserService.Domain.Documents import (
    CellValue,
    DocumentStatus,
    ExtractionRequest,
    Locator,
    ParseWarning,
    ParsedDocument,
    WarningCode,
)
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
from ParserService.Infrastructure.Extraction.XlsxPropertyReader import XlsxPropertyReader


class XlsxExtractor:
    """Extract XLSX and XLSM workbooks using streaming worksheet readers."""

    def __init__(
        self, builder: SpreadsheetTableBuilder, properties: XlsxPropertyReader | None = None
    ) -> None:
        self._builder = builder
        self._properties = properties or XlsxPropertyReader()

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Read all worksheets, retaining readable sheets when one is damaged."""
        try:
            return Result.ok(self._read_workbook(request))
        except (OSError, zipfile.BadZipFile, ValueError):
            return Result.err(FailureReason.CORRUPTED_FILE)

    def _read_workbook(self, request: ExtractionRequest) -> ParsedDocument:
        path = Path(request.source.location)
        request = request.with_properties(self._properties.read(path))
        with path.open("rb") as formulas_file, path.open("rb") as values_file:
            formulas_book = load_workbook(formulas_file, read_only=True, data_only=False, keep_links=False)
            values_book = load_workbook(values_file, read_only=True, data_only=True, keep_links=False)
            try:
                return self._collect_sheets(request, path, formulas_book, values_book)
            finally:
                formulas_book.close()
                values_book.close()

    def _collect_sheets(
        self, request: ExtractionRequest, path: Path, formulas_book: Workbook, values_book: Workbook
    ) -> ParsedDocument:
        sheets, warnings, formulas = self._read_sheets(path, formulas_book, values_book)
        result = self._builder.build(request, sheets, formulas)
        return self._with_warnings(result, warnings, request)

    def _read_sheets(
        self, path: Path, formulas_book: Workbook, values_book: Workbook
    ) -> tuple[list[tuple[str, bool, list[list[object]]]], list[ParseWarning], int]:
        sheets: list[tuple[str, bool, list[list[object]]]] = []
        warnings: list[ParseWarning] = []
        formulas = 0
        for index, name in enumerate(formulas_book.sheetnames, 1):
            matrix, count, warning = self._read_one_sheet(path, index, name, formulas_book, values_book)
            sheets.append(matrix)
            formulas += count
            if warning is not None:
                warnings.append(warning)
        return sheets, warnings, formulas

    def _read_one_sheet(
        self, path: Path, index: int, name: str, formulas_book: Workbook, values_book: Workbook
    ) -> tuple[tuple[str, bool, list[list[object]]], int, ParseWarning | None]:
        sheet = formulas_book[name]
        try:
            matrix, count = self._read_sheet(path, index, sheet, values_book[name])
            return (name, sheet.sheet_state != Worksheet.SHEETSTATE_VISIBLE, matrix), count, None
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, ElementTree.ParseError):
            warning = ParseWarning(WarningCode.SHEET_UNREADABLE, Locator.for_cells(name, None))
            return (name, sheet.sheet_state != Worksheet.SHEETSTATE_VISIBLE, []), 0, warning

    def _with_warnings(
        self, result: ParsedDocument, warnings: Sequence[ParseWarning], request: ExtractionRequest
    ) -> ParsedDocument:
        extra = tuple(warning for warning in result.warnings if warning not in request.detection.warnings)
        combined = tuple(request.detection.warnings) + tuple(warnings) + extra
        if not warnings:
            return result
        return ParsedDocument(DocumentStatus.PARTIAL, result.facts, result.elements, combined, result.outline, result.metrics)

    def _read_sheet(
        self, path: Path, index: int, formulas_sheet: ReadOnlyWorksheet, values_sheet: ReadOnlyWorksheet
    ) -> tuple[list[list[object]], int]:
        merges = self._merged_ranges(path, index)
        matrix: list[list[object]] = []
        formula_count = 0
        formula_rows = formulas_sheet.iter_rows()
        value_rows = values_sheet.iter_rows()
        for formula_row, value_row in zip(formula_rows, value_rows, strict=True):
            output, count = self._read_row(formula_row, value_row)
            matrix.append(output)
            formula_count += count
        self._expand_merges(matrix, merges)
        return matrix, formula_count

    def _read_row(
        self, formula_row: tuple[ReadOnlyCell, ...], value_row: tuple[ReadOnlyCell, ...]
    ) -> tuple[list[object], int]:
        output: list[object] = []
        formula_count = 0
        for formula_cell, value_cell in zip(formula_row, value_row, strict=True):
            value = value_cell.value
            if formula_cell.data_type == "f":
                formula_count += 1
                output.append(CellValue(self._display(value), str(formula_cell.value), self._scalar(value)))
            else:
                output.append(value)
        return output, formula_count

    def _merged_ranges(self, path: Path, index: int) -> tuple[str, ...]:
        with zipfile.ZipFile(path) as archive:
            target = self._worksheet_path(archive, index)
            with archive.open(target) as stream:
                ranges: list[str] = []
                for _, node in ElementTree.iterparse(stream, events=("end",)):
                    if node.tag.endswith("}mergeCell") and "ref" in node.attrib:
                        ranges.append(node.attrib["ref"])
                    node.clear()
                return tuple(ranges)

    def _worksheet_path(self, archive: zipfile.ZipFile, index: int) -> str:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        sheets = workbook.findall(".//{*}sheet")
        relation_id = sheets[index - 1].attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        relation = next(
            node for node in relationships.findall(".//{*}Relationship")
            if node.attrib.get("Id") == relation_id
        )
        target = relation.attrib["Target"]
        return posixpath.normpath(target.lstrip("/")) if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))

    def _expand_merges(self, matrix: list[list[object]], ranges: tuple[str, ...]) -> None:
        for merged_range in ranges:
            min_col, min_row, max_col, max_row = range_boundaries(merged_range)
            value = matrix[min_row - 1][min_col - 1]
            for row_index in range(min_row - 1, max_row):
                while len(matrix[row_index]) < max_col:
                    matrix[row_index].append(None)
                for column_index in range(min_col - 1, max_col):
                    matrix[row_index][column_index] = value

    def _display(self, value: object) -> str | None:
        return None if value is None else str(value)

    def _scalar(self, value: object) -> str | int | float | bool | None:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
