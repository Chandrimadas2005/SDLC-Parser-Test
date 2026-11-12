import dataclasses
from pathlib import Path
from typing import Final

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
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.OcrText import OcrText
from ParserService.Infrastructure.Extraction.PlainTextBlockSplitter import PlainTextBlockSplitter
from ParserService.Infrastructure.Extraction.TesseractOcr import TesseractOcr
from ParserService.Infrastructure.Extraction.TextBlock import TextBlock


class ImageExtractor:
    """Extractor for PNG, JPEG and TIFF images: OCR with a confidence value (brief 2.3).

    Every result carries ``ocr_applied``; a mean confidence below ``LOW_CONFIDENCE``
    adds ``ocr_low_confidence``. The confidence itself is kept in the file properties
    as ``ocr_confidence``. An image with no recognisable text is ``partial`` with
    ``page_unreadable``. Locators are page 1 plus character offsets into the OCR text.
    """

    LOW_CONFIDENCE: Final = 0.6
    CONFIDENCE_PROPERTY: Final = "ocr_confidence"

    def __init__(self, ocr: TesseractOcr, splitter: PlainTextBlockSplitter) -> None:
        self._ocr = ocr
        self._splitter = splitter

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Recognise the text of an image.

        Args:
            request: The image, its facts and its detection.

        Returns:
            The parsed document, or the OCR failure.
        """
        recognised = self._ocr.read(Path(request.source.location))
        if recognised.is_err:
            return Result.err(recognised.unwrap_err())
        return Result.ok(self._document(request, recognised.unwrap()))

    def _document(self, request: ExtractionRequest, ocr: OcrText) -> ParsedDocument:
        blocks = self._splitter.blocks(ocr.text)
        elements = self._elements(blocks)
        words = sum(len(block.content.split()) for block in blocks)
        return ParsedDocument(
            status=DocumentStatus.SUCCEEDED if elements else DocumentStatus.PARTIAL,
            facts=self._facts(request, ocr),
            elements=elements,
            warnings=request.detection.warnings + self._warnings(ocr, found=bool(elements)),
            outline=(),
            metrics=Metrics.for_elements(elements, {MetricName.PAGES: 1, MetricName.WORDS: words}),
        )

    @staticmethod
    def _elements(blocks: list[TextBlock]) -> tuple[Element, ...]:
        return tuple(
            Element(
                ElementId.at(n),
                block.kind,
                Locator(page=1, char_start=block.start, char_end=block.end),
                block.content,
            )
            for n, block in enumerate(blocks, 1)
        )

    def _facts(self, request: ExtractionRequest, ocr: OcrText) -> DocumentFacts:
        confidence = {self.CONFIDENCE_PROPERTY: f"{ocr.confidence:.2f}"}
        properties = {**(request.facts.properties or {}), **confidence}
        return dataclasses.replace(request.facts, page_count=1, properties=properties)

    def _warnings(self, ocr: OcrText, *, found: bool) -> tuple[ParseWarning, ...]:
        page = Locator.for_page(1)
        applied = ParseWarning(WarningCode.OCR_APPLIED, page)
        if not found:
            return (applied, ParseWarning(WarningCode.PAGE_UNREADABLE, page))
        low = ocr.confidence < self.LOW_CONFIDENCE
        return (applied, ParseWarning(WarningCode.OCR_LOW_CONFIDENCE, page)) if low else (applied,)
