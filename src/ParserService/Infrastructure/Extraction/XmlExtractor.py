from typing import Final
from xml.etree.ElementTree import Element, ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.StructuredDataBuilder import StructuredDataBuilder
from ParserService.Infrastructure.Extraction.StructuredField import StructuredField
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader


class XmlExtractor:
    """Extracts XML without DTDs or external entity processing.

    Attributes become ``@name`` fields and text mixed between child elements becomes a
    ``#text`` field, so no content is dropped silently.
    """

    SEPARATOR: Final = " "

    def __init__(self, reader: TextFileReader, builder: StructuredDataBuilder) -> None:
        self._reader = reader
        self._builder = builder

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Parse XML with defusedxml and map its root element's content."""
        source = self._reader.read(request)
        if self._builder.is_empty(source):
            return self._builder.empty(request, source)
        try:
            root = ElementTree.fromstring(source)
        except DefusedXmlException:
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        except (ParseError, ValueError):
            return Result.err(FailureReason.CORRUPTED_FILE)
        return self._from_root(request, source, root)

    def _from_root(
        self, request: ExtractionRequest, source: str, root: Element
    ) -> Result[ParsedDocument, FailureReason]:
        if self._exceeds_limits(root):
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        return self._builder.result(request, source, self._children(root))

    def _exceeds_limits(self, root: Element) -> bool:
        pending = [(root, 1)]
        count = 0
        while pending:
            element, depth = pending.pop()
            count += 1
            if depth > self._builder.max_depth or count > self._builder.max_nodes:
                return True
            pending.extend((child, depth + 1) for child in element)
        return False

    def _children(self, root: Element) -> dict[str, object]:
        value = self._value(root)
        return value if isinstance(value, dict) else {str(root.tag): value}

    def _value(self, element: Element) -> str | dict[str, object]:
        prefix = StructuredField.XML_ATTRIBUTE_PREFIX.value
        values: dict[str, object] = {f"{prefix}{k}": v for k, v in element.attrib.items()}
        text = self._text(element)
        if len(element) == 0 and not values:
            return text
        for child in element:
            self._add(values, str(child.tag), self._value(child))
        if text:
            values[StructuredField.XML_TEXT.value] = text
        return values

    def _text(self, element: Element) -> str:
        parts = [element.text or "", *(child.tail or "" for child in element)]
        return self.SEPARATOR.join(part.strip() for part in parts if part.strip())

    @staticmethod
    def _add(values: dict[str, object], name: str, value: object) -> None:
        existing = values.get(name)
        if existing is None:
            values[name] = value
            return
        if isinstance(existing, list):
            existing.append(value)
            return
        values[name] = [existing, value]
