import dataclasses
from collections.abc import Iterator

from ParserService.Domain.Documents.DocumentFacts import DocumentFacts
from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.Element import Element
from ParserService.Domain.Documents.ElementId import ElementId
from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.Locator import Locator
from ParserService.Domain.Documents.MetricName import MetricName
from ParserService.Domain.Documents.Metrics import Metrics
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Infrastructure.Extraction.OcrConfidence import OcrConfidence
from ParserService.Infrastructure.Extraction.PdfContent import PdfContent
from ParserService.Infrastructure.Extraction.PlainTextBlockSplitter import PlainTextBlockSplitter
from ParserService.Infrastructure.Extraction.TextBlock import TextBlock


class PdfDocumentAssembler:
    """Turns the pages of a PDF into a ``ParsedDocument``.

    Each paragraph of a page's text layer becomes one element whose locator is the
    page and the character span inside that page's text. A page with no text layer
    or that failed to load is reported with ``page_unreadable`` and the result is
    ``partial``. A page read with OCR adds ``ocr_applied`` (and ``ocr_low_confidence``
    below the threshold); the mean OCR confidence is kept in the file properties.
    """

    def __init__(self, splitter: PlainTextBlockSplitter) -> None:
        self._splitter = splitter

    def build(self, request: ExtractionRequest, content: PdfContent) -> ParsedDocument:
        """Build the result for a PDF.

        Args:
            request: The file, its facts and its detection.
            content: The text of every page and the outline.

        Returns:
            The parsed document, ``partial`` when any page has no readable text.
        """
        elements = tuple(
            self._element(n, page, block)
            for n, (page, block) in enumerate(self._blocks(content), 1)
        )
        unreadable = tuple(self._unreadable(content))
        ocr = tuple(self._ocr_warnings(content))
        words = sum(len(element.text.split()) for element in elements if element.text)
        counts = {MetricName.PAGES: len(content.pages), MetricName.WORDS: words}
        return ParsedDocument(
            status=DocumentStatus.PARTIAL if unreadable else DocumentStatus.SUCCEEDED,
            facts=self._facts(request, content),
            elements=elements,
            warnings=request.detection.warnings + ocr + unreadable,
            outline=content.outline,
            metrics=Metrics.for_elements(elements, counts),
        )

    @staticmethod
    def _element(position: int, page: int, block: TextBlock) -> Element:
        locator = Locator(page=page, char_start=block.start, char_end=block.end)
        text = block.content.replace("\r\n", "\n")
        return Element(ElementId.at(position), block.kind, locator, text)

    def _blocks(self, content: PdfContent) -> Iterator[tuple[int, TextBlock]]:
        for page in content.pages:
            for block in self._splitter.blocks(page.text or ""):
                yield page.number, block

    @staticmethod
    def _ocr_warnings(content: PdfContent) -> Iterator[ParseWarning]:
        for page in content.pages:
            if page.ocr_confidence is None:
                continue
            locator = Locator.for_page(page.number)
            yield ParseWarning(WarningCode.OCR_APPLIED, locator)
            if page.ocr_confidence < OcrConfidence.LOW:
                yield ParseWarning(WarningCode.OCR_LOW_CONFIDENCE, locator)

    @staticmethod
    def _facts(request: ExtractionRequest, content: PdfContent) -> DocumentFacts:
        scores = [p.ocr_confidence for p in content.pages if p.ocr_confidence is not None]
        facts = dataclasses.replace(request.facts, page_count=len(content.pages))
        if not scores:
            return facts
        mean = {OcrConfidence.PROPERTY: f"{sum(scores) / len(scores):.2f}"}
        return dataclasses.replace(facts, properties={**(facts.properties or {}), **mean})

    @staticmethod
    def _unreadable(content: PdfContent) -> Iterator[ParseWarning]:
        for page in content.pages:
            if not (page.text or "").strip():
                yield ParseWarning(WarningCode.PAGE_UNREADABLE, Locator.for_page(page.number))
