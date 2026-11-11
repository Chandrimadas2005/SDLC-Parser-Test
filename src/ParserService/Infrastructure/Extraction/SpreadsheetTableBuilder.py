import re
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime
from typing import Final

from ParserService.Domain.Documents import (
    CellValue,
    ColumnProfile,
    ColumnType,
    Confidence,
    DocumentStatus,
    Element,
    ElementId,
    ElementKind,
    ExtractionRequest,
    Locator,
    MetricName,
    Metrics,
    OutlineEntry,
    OutlineKind,
    ParsedDocument,
    ParseWarning,
    Table,
    TableRow,
    WarningCode,
)


class SpreadsheetTableBuilder:
    """Build source-located spreadsheet tables and infer column profiles."""

    ID_PATTERN = re.compile(r"^(?=.*\d)[A-Za-z0-9_-]{5,}$")
    HEADER_THRESHOLD: Final = 0.75

    def build(
        self,
        request: ExtractionRequest,
        sheets: Sequence[tuple[str, bool, Sequence[Sequence[object]]]],
        formulas: int,
    ) -> ParsedDocument:
        """Create a document from rows streamed from each sheet."""
        elements, outline, warnings, rows, columns, hidden = self._build_sheets(sheets)
        counts = self._counts((len(sheets), rows, columns, formulas, hidden))
        status = self._status(warnings)
        facts = replace(request.facts, sheet_count=len(sheets))
        return ParsedDocument(
            status,
            facts,
            tuple(elements),
            tuple(warnings),
            tuple(outline),
            Metrics.for_elements(elements, counts),
        )

    def _build_sheets(
        self, sheets: Sequence[tuple[str, bool, Sequence[Sequence[object]]]]
    ) -> tuple[list[Element], list[OutlineEntry], list[ParseWarning], int, int, int]:
        elements: list[Element] = []
        outline: list[OutlineEntry] = []
        warnings: list[ParseWarning] = []
        rows = columns = hidden = 0
        for name, is_hidden, matrix in sheets:
            sheet = (name, is_hidden, matrix)
            element, entry, guessed, row_count, column_count = self._build_sheet(
                sheet, len(elements) + 1
            )
            elements.append(element)
            outline.append(entry)
            rows += row_count
            columns += column_count
            hidden += int(is_hidden)
            if guessed:
                warnings.append(ParseWarning(WarningCode.HEADER_ROW_GUESSED, element.locator))
        return elements, outline, warnings, rows, columns, hidden

    def _build_sheet(
        self, sheet: tuple[str, bool, Sequence[Sequence[object]]], position: int
    ) -> tuple[Element, OutlineEntry, bool, int, int]:
        name, hidden, matrix = sheet
        locator = self._locator(name, matrix)
        table, guessed, rows, columns = self._table(matrix)
        element = Element(ElementId.at(position), ElementKind.TABLE, locator, table=table)
        entry = OutlineEntry(OutlineKind.SHEET, name, locator, hidden=hidden)
        return element, entry, guessed, rows, columns

    @staticmethod
    def _counts(totals: tuple[int, int, int, int, int]) -> dict[MetricName, int]:
        sheets, rows, columns, formulas, hidden = totals
        return {
            MetricName.SHEETS: sheets,
            MetricName.ROWS: rows,
            MetricName.COLUMNS: columns,
            MetricName.FORMULAS: formulas,
            MetricName.HIDDEN_SHEETS: hidden,
        }

    def _status(self, warnings: Sequence[ParseWarning]) -> DocumentStatus:
        return (
            DocumentStatus.PARTIAL
            if any(warning.code is WarningCode.SHEET_UNREADABLE for warning in warnings)
            else DocumentStatus.SUCCEEDED
        )

    def _table(self, matrix: Sequence[Sequence[object]]) -> tuple[Table, bool, int, int]:
        width = max((len(row) for row in matrix), default=0)
        rows = [list(row) + [None] * (width - len(row)) for row in matrix]
        header, confidence = self._header(rows[0] if rows else [])
        names = self._names(rows[0], width) if header else self._column_names(width)
        data = rows[1:] if header else rows
        profiles = self._profiles(data, names)
        table_rows = tuple(
            self._row(index + (2 if header else 1), row, names) for index, row in enumerate(data)
        )
        table = Table(table_rows, 1 if header else None, confidence if header else None, profiles)
        return table, not header and bool(rows), len(data), width

    def _header(self, row: Sequence[object]) -> tuple[bool, Confidence]:
        values = [value for value in row if value not in (None, "")]
        if not values:
            return False, Confidence(0.0)
        text_ratio = sum(isinstance(value, str) for value in values) / len(values)
        unique_ratio = len({str(value).strip().casefold() for value in values}) / len(values)
        confidence = text_ratio * unique_ratio
        return confidence >= self.HEADER_THRESHOLD, Confidence(min(confidence, 1.0))

    def _names(self, row: Sequence[object], width: int) -> tuple[str, ...]:
        names: list[str] = []
        for index in range(width):
            base = str(row[index]).strip() if row[index] not in (None, "") else f"Column{index + 1}"
            names.append(self._unique_name(base, names))
        return tuple(names)

    def _unique_name(self, name: str, previous: Sequence[str]) -> str:
        candidate = name
        suffix = 2
        while candidate in previous:
            candidate = f"{name}_{suffix}"
            suffix += 1
        return candidate

    def _column_names(self, width: int) -> tuple[str, ...]:
        return tuple(f"Column{index + 1}" for index in range(width))

    def _row(self, number: int, values: Sequence[object], names: Sequence[str]) -> TableRow:
        cells = {names[index]: self._cell(value) for index, value in enumerate(values)}
        return TableRow(number, cells)

    def _cell(self, value: object) -> str | CellValue:
        if isinstance(value, CellValue):
            return value
        return "" if value is None else self._string(value)

    def _string(self, value: object) -> str:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    def _profiles(
        self, data: Sequence[Sequence[object]], names: Sequence[str]
    ) -> tuple[ColumnProfile, ...]:
        return tuple(self._profile(index, name, data) for index, name in enumerate(names))

    def _profile(self, index: int, name: str, rows: Sequence[Sequence[object]]) -> ColumnProfile:
        values = [
            self._profile_value(row[index])
            for row in rows
            if index < len(row)
            and row[index] not in (None, "")
            and self._profile_value(row[index]) not in (None, "")
        ]
        kinds = {self._kind(value) for value in values}
        guessed = next(iter(kinds)) if len(kinds) == 1 else ColumnType.MIXED
        if not values:
            guessed = ColumnType.EMPTY
        unique = len({self._string(value) for value in values})
        fill = len(values) / len(rows) if rows else 0.0
        looks_like_id = bool(values) and all(
            self.ID_PATTERN.match(self._string(value)) for value in values
        )
        return ColumnProfile(name, guessed, fill, unique, looks_like_id)

    def _profile_value(self, value: object) -> object:
        if isinstance(value, CellValue):
            return value.calculated_value if value.calculated_value is not None else value.value
        return value

    def _kind(self, value: object) -> ColumnType:
        if isinstance(value, bool) or str(value).strip().casefold() in {
            "true",
            "false",
            "yes",
            "no",
        }:
            return ColumnType.BOOLEAN
        if isinstance(value, (int, float)) or re.fullmatch(
            r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", str(value).strip()
        ):
            return ColumnType.NUMBER
        if isinstance(value, (date, datetime)) or re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", str(value).strip()
        ):
            return ColumnType.DATE
        return ColumnType.TEXT

    def _locator(self, name: str, matrix: Sequence[Sequence[object]]) -> Locator:
        rows = max(len(matrix), 1)
        columns = max((len(row) for row in matrix), default=1)
        return Locator.for_cells(name, f"A1:{self._column_letter(columns)}{rows}")

    def _column_letter(self, number: int) -> str:
        result = ""
        while number:
            number, remainder = divmod(number - 1, 26)
            result = chr(65 + remainder) + result
        return result
