import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, cast

from ParserService.Domain.Documents.Confidence import Confidence
from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.Element import Element
from ParserService.Domain.Documents.ElementId import ElementId
from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.Locator import Locator
from ParserService.Domain.Documents.MetricName import MetricName
from ParserService.Domain.Documents.Metrics import Metrics
from ParserService.Domain.Documents.OutlineEntry import OutlineEntry
from ParserService.Domain.Documents.OutlineKind import OutlineKind
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.Table import Table
from ParserService.Domain.Documents.TableRow import TableRow
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Config.Limits import Limits
from ParserService.Infrastructure.Extraction.StructuredField import StructuredField


@dataclass(frozen=True, slots=True)
class _BuildContext:
    source: str
    elements: list[Element] = field(default_factory=list)
    outline: list[OutlineEntry] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _TopLevel:
    name: str
    value: object
    cursor: int


@dataclass(frozen=True, slots=True)
class _Value:
    value: object
    path: str
    cursor: int
    depth: int


class StructuredDataBuilder:
    """Builds source-located elements from JSON-, YAML- and XML-like values.

    Each value is searched for after its own key and after the value before it, so a
    value that appears several times points at its own occurrence.
    """

    EMPTY: Final = ""
    NULL: Final = "null"

    def __init__(self, limits: Limits | None = None) -> None:
        chosen = limits or Limits()
        self.max_depth = chosen.structured_max_depth
        self.max_nodes = chosen.structured_max_nodes

    def result(
        self, request: ExtractionRequest, source: str, values: object
    ) -> Result[ParsedDocument, FailureReason]:
        """Check the safety limits, then build the document from loaded values.

        Args:
            request: The extraction request with the file facts and detection.
            source: The decoded source text, used for character locators.
            values: The loaded JSON, YAML or XML values.

        Returns:
            The parsed document, or ``LIMIT_EXCEEDED`` for too deep or too large input.
            An empty document (``None``) gives a result without elements.
        """
        if values is None:
            return self.empty(request, source)
        mapping = self._as_mapping(values)
        if self.exceeds_limits(mapping):
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        return Result.ok(self.build(request, source, mapping))

    def empty(
        self, request: ExtractionRequest, source: str
    ) -> Result[ParsedDocument, FailureReason]:
        """Return a succeeded document without elements, as for any other empty file."""
        return Result.ok(self.build(request, source, {}))

    @staticmethod
    def is_empty(source: str) -> bool:
        """Return whether the decoded source holds nothing but whitespace."""
        return not source.strip()

    def exceeds_limits(self, values: object) -> bool:
        """Return whether nested input exceeds the configured safety limits."""
        pending: list[tuple[object, int, frozenset[int]]] = [(values, 1, frozenset())]
        count = 0
        while pending:
            value, depth, ancestors = pending.pop()
            count += 1
            if depth > self.max_depth or count > self.max_nodes or id(value) in ancestors:
                return True
            children = self._children(value)
            branch = ancestors | {id(value)} if children else ancestors
            pending.extend((child, depth + 1, branch) for child in children)
        return False

    @staticmethod
    def _as_mapping(values: object) -> Mapping[str, object]:
        if isinstance(values, Mapping):
            mapping = cast("Mapping[object, object]", values)
            return {str(key): value for key, value in mapping.items()}
        return {StructuredField.ROOT.value: values}

    @staticmethod
    def _children(value: object) -> list[object]:
        if isinstance(value, Mapping):
            return list(cast("Mapping[object, object]", value).values())
        return cast("list[object]", value) if isinstance(value, list) else []

    def build(
        self, request: ExtractionRequest, source: str, values: Mapping[str, object]
    ) -> ParsedDocument:
        """Convert top-level keys and their values into a parsed document."""
        context = _BuildContext(source)
        cursor = 0
        for name, value in values.items():
            cursor = self._append_top_level(context, _TopLevel(name, value, cursor))
        words = sum(len((element.text or self.EMPTY).split()) for element in context.elements)
        return ParsedDocument(
            DocumentStatus.SUCCEEDED,
            request.facts,
            tuple(context.elements),
            request.detection.warnings,
            tuple(context.outline),
            Metrics.for_elements(context.elements, {MetricName.WORDS: words}),
        )

    def _append_top_level(self, context: _BuildContext, item: _TopLevel) -> int:
        start = self._find(context.source, item.name, item.cursor)
        end = min(len(context.source), start + len(item.name))
        locator = Locator.for_text(len(context.elements) + 1, start, end)
        heading = Element(
            ElementId.at(len(context.elements) + 1), ElementKind.HEADING, locator, item.name, 1
        )
        context.elements.append(heading)
        context.outline.append(OutlineEntry(OutlineKind.HEADING, item.name, locator, 1))
        node = _Value(item.value, item.name, start, 1)
        if self._is_object_rows(item.value):
            self._append_table(context, node)
        else:
            self._append_values(context, _Value(item.value, item.name, end, 1))
        return self._last_end(context, end)

    def _append_values(self, context: _BuildContext, node: _Value) -> None:
        if node.depth > self.max_depth or len(context.elements) > self.max_nodes:
            return
        if isinstance(node.value, Mapping):
            self._append_mapping(context, node)
            return
        if not isinstance(node.value, list):
            self._append_paragraph(context, node)
            return
        self._append_sequence(context, node)

    def _append_sequence(self, context: _BuildContext, node: _Value) -> None:
        if self._is_object_rows(node.value):
            self._append_table(context, node)
            return
        self._append_list(context, node)

    def _append_mapping(self, context: _BuildContext, node: _Value) -> None:
        values = cast("Mapping[object, object]", node.value)
        cursor = node.cursor
        for key, child in values.items():
            name = str(key)
            cursor = self._after(context.source, name, cursor)
            nested = _Value(child, f"{node.path}.{name}", cursor, node.depth + 1)
            self._append_values(context, nested)
            cursor = self._last_end(context, cursor)

    def _append_list(self, context: _BuildContext, node: _Value) -> None:
        values = cast("list[object]", node.value)
        cursor = node.cursor
        for index, child in enumerate(values):
            nested = _Value(child, f"{node.path}[{index}]", cursor, node.depth + 1)
            self._append_values(context, nested)
            cursor = self._last_end(context, cursor)

    def _append_table(self, context: _BuildContext, node: _Value) -> None:
        rows = cast("list[Mapping[object, object]]", node.value)
        keys = tuple(rows[0].keys())
        data = tuple(self._row(index + 2, row, keys) for index, row in enumerate(rows))
        table = Table(data, header_row=1, header_confidence=Confidence(1.0))
        cells = [self._scalar(row.get(key)) for row in rows for key in keys]
        end = self._span_end(context.source, cells, node.cursor + len(node.path))
        locator = Locator.for_text(len(context.elements) + 1, node.cursor, end)
        table_element = Element(
            ElementId.at(len(context.elements) + 1), ElementKind.TABLE, locator, table=table
        )
        context.elements.append(table_element)

    def _append_paragraph(self, context: _BuildContext, node: _Value) -> None:
        scalar = self._scalar(node.value)
        start = self._find(context.source, scalar, node.cursor)
        end = min(len(context.source), start + max(1, len(scalar)))
        locator = Locator.for_text(len(context.elements) + 1, start, end)
        paragraph = Element(
            ElementId.at(len(context.elements) + 1),
            ElementKind.PARAGRAPH,
            locator,
            f"{node.path}: {scalar}",
        )
        context.elements.append(paragraph)

    @staticmethod
    def _is_object_rows(value: object) -> bool:
        if not isinstance(value, list) or not value:
            return False
        if not all(isinstance(row, Mapping) for row in value):
            return False
        rows = cast("list[object]", value)
        first = cast("Mapping[str, object]", rows[0])
        return all(
            set(cast("Mapping[str, object]", row).keys()) == set(first.keys())
            for row in rows
            if isinstance(row, Mapping)
        )

    def _row(self, number: int, row: Mapping[object, object], keys: tuple[object, ...]) -> TableRow:
        return TableRow(number, {str(key): self._scalar(row.get(key)) for key in keys})

    @classmethod
    def _scalar(cls, value: object) -> str:
        if value is None:
            return cls.NULL
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return str(value).lower() if isinstance(value, bool) else str(value)

    @classmethod
    def _span_end(cls, source: str, cells: list[str], cursor: int) -> int:
        for cell in cells:
            cursor = cls._after(source, cell, cursor)
        return min(len(source), cursor)

    @staticmethod
    def _last_end(context: _BuildContext, cursor: int) -> int:
        last = context.elements[-1].locator.char_end if context.elements else None
        return cursor if last is None else max(cursor, last)

    @staticmethod
    def _after(source: str, needle: str, cursor: int) -> int:
        found = source.find(needle, cursor)
        return cursor if found < 0 else found + len(needle)

    @staticmethod
    def _find(source: str, needle: str, cursor: int) -> int:
        found = source.find(needle, cursor)
        return max(0, cursor) if found < 0 else found
