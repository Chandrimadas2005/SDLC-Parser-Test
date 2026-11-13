from collections.abc import Sequence
from typing import Final

from bs4 import BeautifulSoup

from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.Element import Element
from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.Locator import Locator
from ParserService.Domain.Documents.MetricName import MetricName
from ParserService.Domain.Documents.Metrics import Metrics
from ParserService.Domain.Documents.OutlineEntry import OutlineEntry
from ParserService.Domain.Documents.OutlineKind import OutlineKind
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Infrastructure.Extraction.Html.HtmlBlockReader import HtmlBlockReader
from ParserService.Infrastructure.Extraction.Html.HtmlElementPlacer import HtmlElementPlacer
from ParserService.Infrastructure.Extraction.Html.HtmlMetadataReader import HtmlMetadataReader
from ParserService.Infrastructure.Extraction.Html.HtmlReading import HtmlReading


class HtmlDocumentBuilder:
    """Builds the ``ParsedDocument`` of an HTML file from its parsed tree.

    Elements come in reading order with stable ids and locators; headings form the
    outline. Every skipped script, frame, embedded object or unsafe link adds an
    ``element_skipped`` warning that points at the paragraph it sits in. Skipping
    active content loses no document text, so the result is ``succeeded``; detection
    warnings, such as an extension mismatch, are carried over.
    """

    INLINE_KINDS: Final = frozenset({ElementKind.LINK, ElementKind.IMAGE})

    def __init__(
        self, reader: HtmlBlockReader, placer: HtmlElementPlacer, metadata: HtmlMetadataReader
    ) -> None:
        self._reader = reader
        self._placer = placer
        self._metadata = metadata

    def build(self, request: ExtractionRequest, soup: BeautifulSoup) -> ParsedDocument:
        """Build the result for one HTML document.

        Args:
            request: The file, its facts and its detection.
            soup: The parsed document.

        Returns:
            A succeeded ``ParsedDocument``.
        """
        reading = self._reader.read(soup)
        elements = self._placer.place(reading.blocks)
        return ParsedDocument(
            status=DocumentStatus.SUCCEEDED,
            facts=self._metadata.facts(request.facts, soup),
            elements=elements,
            warnings=(*request.detection.warnings, *self._skipped(reading)),
            outline=self._outline(elements),
            metrics=Metrics.for_elements(elements, {MetricName.WORDS: self._words(elements)}),
        )

    @staticmethod
    def _skipped(reading: HtmlReading) -> tuple[ParseWarning, ...]:
        last = reading.paragraph_count
        return tuple(
            ParseWarning(WarningCode.ELEMENT_SKIPPED, Locator(paragraph=min(position, last)))
            if last
            else ParseWarning(WarningCode.ELEMENT_SKIPPED)
            for position in reading.skipped
        )

    @staticmethod
    def _outline(elements: Sequence[Element]) -> tuple[OutlineEntry, ...]:
        return tuple(
            OutlineEntry(OutlineKind.HEADING, element.text, element.locator, element.level)
            for element in elements
            if element.kind is ElementKind.HEADING and element.text
        )

    def _words(self, elements: Sequence[Element]) -> int:
        return sum(self._element_words(element) for element in elements)

    def _element_words(self, element: Element) -> int:
        if element.table is not None:
            cells = (value for row in element.table.rows for value in row.cells.values())
            return sum(len(str(value).split()) for value in cells)
        if element.kind in self.INLINE_KINDS:
            return 0
        return len((element.text or "").split())
