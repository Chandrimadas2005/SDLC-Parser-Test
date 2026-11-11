import posixpath
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell, MergedCell
from openpyxl.utils.cell import range_boundaries
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from ParserService.Domain.Documents import (
    CellValue,
    DocumentStatus,
    ExtractionRequest,
    Locator,
    ParsedDocument,
    ParseWarning,
    WarningCode,
)
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
from ParserService.Infrastructure.Extraction.XlsxPropertyReader import XlsxPropertyReader


@dataclass(frozen=True, slots=True)
class _Workbooks:
    """One workbook opened twice: once for formulas, once for their calculated values."""

    path: Path
    formulas: Workbook
    values: Workbook


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
            formulas_book = load_workbook(
                formulas_file, read_only=True, data_only=False, keep_links=False
            )
            values_book = load_workbook(
                values_file, read_only=True, data_only=True, keep_links=False
            )
            try:
                books = _Workbooks(path, formulas_book, values_book)
                return self._collect_sheets(request, books)
            finally:
                formulas_book.close()
                values_book.close()

    def _collect_sheets(self, request: ExtractionRequest, books: _Workbooks) -> ParsedDocument:
        sheets, warnings, formulas = self._read_sheets(books)
        result = self._builder.build(request, sheets, formulas)
        return self._with_warnings(result, warnings, request)

    def _read_sheets(
        self, books: _Workbooks
    ) -> tuple[list[tuple[str, bool, list[list[object]]]], list[ParseWarning], int]:
        sheets: list[tuple[str, bool, list[list[object]]]] = []
        warnings: list[ParseWarning] = []
        formulas = 0
        for index in range(1, len(books.formulas.sheetnames) + 1):
            matrix, count, warning = self._read_one_sheet(books, index)
            sheets.append(matrix)
            formulas += count
            if warning is not None:
                warnings.append(warning)
        return sheets, warnings, formulas

    def _read_one_sheet(
        self, books: _Workbooks, index: int
    ) -> tuple[tuple[str, bool, list[list[object]]], int, ParseWarning | None]:
        name = books.formulas.sheetnames[index - 1]
        hidden = books.formulas[name].sheet_state != Worksheet.SHEETSTATE_VISIBLE
        try:
            matrix, count = self._read_sheet(books, index)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, ElementTree.ParseError):
            warning = ParseWarning(WarningCode.SHEET_UNREADABLE, Locator.for_cells(name, None))
            return (name, hidden, []), 0, warning
        return (name, hidden, matrix), count, None

    def _with_warnings(
        self, result: ParsedDocument, warnings: Sequence[ParseWarning], request: ExtractionRequest
    ) -> ParsedDocument:
        extra = tuple(
            warning for warning in result.warnings if warning not in request.detection.warnings
        )
        combined = tuple(request.detection.warnings) + tuple(warnings) + extra
        if not warnings:
            return result
        return ParsedDocument(
            DocumentStatus.PARTIAL,
            result.facts,
            result.elements,
            combined,
            result.outline,
            result.metrics,
        )

    def _read_sheet(self, books: _Workbooks, index: int) -> tuple[list[list[object]], int]:
        name = books.formulas.sheetnames[index - 1]
        merges = self._merged_ranges(books.path, index)
        matrix: list[list[object]] = []
        formula_count = 0
        formula_rows = books.formulas[name].iter_rows()
        value_rows = books.values[name].iter_rows()
        for formula_row, value_row in zip(formula_rows, value_rows, strict=True):
            output, count = self._read_row(formula_row, value_row)
            matrix.append(output)
            formula_count += count
        self._expand_merges(matrix, merges)
        return matrix, formula_count

    def _read_row(
        self, formula_row: tuple[Cell | MergedCell, ...], value_row: tuple[Cell | MergedCell, ...]
    ) -> tuple[list[object], int]:
        output: list[object] = []
        formula_count = 0
        for formula_cell, value_cell in zip(formula_row, value_row, strict=True):
            value = value_cell.value
            if formula_cell.data_type == "f":
                formula_count += 1
                output.append(
                    CellValue(self._display(value), str(formula_cell.value), self._scalar(value))
                )
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
        relation_id = sheets[index - 1].attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        relation = next(
            node
            for node in relationships.findall(".//{*}Relationship")
            if node.attrib.get("Id") == relation_id
        )
        target = relation.attrib["Target"]
        return (
            posixpath.normpath(target.lstrip("/"))
            if target.startswith("/")
            else posixpath.normpath(posixpath.join("xl", target))
        )

    def _expand_merges(self, matrix: list[list[object]], ranges: tuple[str, ...]) -> None:
        for merged_range in ranges:
            self._fill_range(matrix, merged_range)

    @staticmethod
    def _fill_range(matrix: list[list[object]], merged_range: str) -> None:
        min_col, min_row, max_col, max_row = (b or 1 for b in range_boundaries(merged_range))
        value = matrix[min_row - 1][min_col - 1]
        for row_index in range(min_row - 1, max_row):
            row = matrix[row_index]
            row.extend([None] * (max_col - len(row)))
            row[min_col - 1 : max_col] = [value] * (max_col - min_col + 1)

    def _display(self, value: object) -> str | None:
        return None if value is None else str(value)

    def _scalar(self, value: object) -> str | int | float | bool | None:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
