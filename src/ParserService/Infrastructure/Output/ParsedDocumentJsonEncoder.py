import json
from collections.abc import Mapping

from ParserService.Domain.Documents import (
    CellValue,
    ColumnProfile,
    DocumentFacts,
    Element,
    Locator,
    MetricName,
    Metrics,
    OutlineEntry,
    ParsedDocument,
    ParseWarning,
    Table,
)
from ParserService.Infrastructure.Output.OutputField import OutputField

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None
type JsonObject = dict[str, JsonValue]


class ParsedDocumentJsonEncoder:
    """Turns a ``ParsedDocument`` into its JSON form (schema v1, brief section 2.3).

    Optional fields that have no value are left out rather than written as
    ``null``. Table data sits directly on its table element, and the format counts
    sit directly in ``metrics``, as in the brief's example. Field order is fixed,
    so the same document always gives the same text.
    """

    INDENT = 2

    def to_json(self, document: ParsedDocument) -> str:
        """Encode a document as JSON text.

        Args:
            document: The parse result.

        Returns:
            The JSON text, UTF-8 safe, ending with a newline.
        """
        return json.dumps(self.encode(document), ensure_ascii=False, indent=self.INDENT) + "\n"

    def encode(self, document: ParsedDocument) -> JsonObject:
        """Encode a document as plain JSON data.

        Args:
            document: The parse result.

        Returns:
            A dictionary that ``json.dumps`` can write directly.
        """
        head: JsonObject = {
            OutputField.SCHEMA_VERSION: document.SCHEMA_VERSION,
            OutputField.STATUS: document.status,
            OutputField.FAILURE_REASON: document.failure_reason,
        }
        return self._without_empty(head) | {
            OutputField.DOCUMENT: self._facts(document.facts),
            OutputField.WARNINGS: [self._warning(warning) for warning in document.warnings],
            OutputField.OUTLINE: [self._outline(entry) for entry in document.outline],
            OutputField.ELEMENTS: [self._element(element) for element in document.elements],
            OutputField.METRICS: self._metrics(document.metrics),
        }

    def _facts(self, facts: DocumentFacts) -> JsonObject:
        return self._without_empty(
            {
                OutputField.FILE_NAME: str(facts.file_name),
                OutputField.DETECTED_TYPE: facts.detected_type,
                OutputField.SIZE_BYTES: facts.size_bytes,
                OutputField.SHA256: str(facts.sha256),
                OutputField.PAGE_COUNT: facts.page_count,
                OutputField.SHEET_COUNT: facts.sheet_count,
                OutputField.SLIDE_COUNT: facts.slide_count,
                OutputField.LANGUAGE: facts.language,
            }
        ) | {OutputField.PROPERTIES: dict(facts.properties or {})}

    def _warning(self, warning: ParseWarning) -> JsonObject:
        locator = None if warning.locator is None else self._locator(warning.locator)
        return self._without_empty({OutputField.CODE: warning.code, OutputField.LOCATOR: locator})

    def _outline(self, entry: OutlineEntry) -> JsonObject:
        return self._without_empty(
            {
                OutputField.KIND: entry.kind,
                OutputField.NAME: entry.name,
                OutputField.LEVEL: entry.level,
                OutputField.HIDDEN: entry.hidden,
                OutputField.LOCATOR: self._locator(entry.locator),
            }
        )

    def _element(self, element: Element) -> JsonObject:
        table = {} if element.table is None else self._table(element.table)
        return (
            self._without_empty(
                {
                    OutputField.ID: str(element.element_id),
                    OutputField.KIND: element.kind,
                    OutputField.LOCATOR: self._locator(element.locator),
                    OutputField.TEXT: element.text,
                    OutputField.LEVEL: element.level,
                }
            )
            | table
        )

    def _table(self, table: Table) -> JsonObject:
        confidence = None if table.header_confidence is None else table.header_confidence.value
        rows: list[JsonValue] = [
            {OutputField.ROW: row.row, OutputField.CELLS: self._cells(row.cells)}
            for row in table.rows
        ]
        profiles: list[JsonValue] = [
            self._column_profile(profile) for profile in table.column_profiles
        ]
        return self._without_empty(
            {
                OutputField.HEADER_ROW: table.header_row,
                OutputField.HEADER_CONFIDENCE: confidence,
            }
        ) | {OutputField.ROWS: rows, OutputField.COLUMN_PROFILES: profiles}

    def _cells(self, cells: Mapping[str, str | CellValue]) -> JsonObject:
        return {
            name: self._cell(value) if isinstance(value, CellValue) else value
            for name, value in cells.items()
        }

    def _cell(self, cell: CellValue) -> JsonValue:
        if cell.formula is None and cell.calculated_value is None:
            return cell.value
        return self._without_empty(
            {
                OutputField.VALUE: cell.value,
                OutputField.FORMULA: cell.formula,
                OutputField.CALCULATED_VALUE: cell.calculated_value,
            }
        )

    def _column_profile(self, profile: ColumnProfile) -> JsonObject:
        return {
            OutputField.NAME: profile.name,
            OutputField.GUESSED_TYPE: profile.guessed_type,
            OutputField.FILL_RATE: profile.fill_rate,
            OutputField.UNIQUE_VALUES: profile.unique_values,
            OutputField.LOOKS_LIKE_ID: profile.looks_like_id,
        }

    def _locator(self, locator: Locator) -> JsonObject:
        return self._without_empty(
            {
                OutputField.PAGE: locator.page,
                OutputField.SHEET: locator.sheet,
                OutputField.RANGE: locator.cell_range,
                OutputField.SLIDE: locator.slide,
                OutputField.PARAGRAPH: locator.paragraph,
                OutputField.CHAR_START: locator.char_start,
                OutputField.CHAR_END: locator.char_end,
            }
        )

    def _metrics(self, metrics: Metrics) -> JsonObject:
        counts: JsonObject = {
            name: metrics.counts[name] for name in MetricName if name in metrics.counts
        }
        by_kind: JsonObject = {str(kind): count for kind, count in metrics.elements_by_kind.items()}
        return counts | {OutputField.ELEMENTS_BY_KIND: by_kind}

    @staticmethod
    def _without_empty(fields: JsonObject) -> JsonObject:
        return {name: value for name, value in fields.items() if value is not None}
