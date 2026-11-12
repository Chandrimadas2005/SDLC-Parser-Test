import dataclasses
from collections.abc import Iterator, Sequence

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
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Infrastructure.Extraction.PptxSlide import PptxSlide
from ParserService.Infrastructure.Extraction.SlideBlock import SlideBlock
from ParserService.Infrastructure.Extraction.TextTableBuilder import TextTableBuilder


class PptxDocumentAssembler:
    """Turns PPTX slides into a ``ParsedDocument``.

    Every element is located by its slide. The slide title is a level-1 heading,
    and every slide is in the outline (its title, or "Slide N" without one). An
    unreadable slide adds ``slide_unreadable`` and makes the result ``partial``.
    """

    def __init__(self, tables: TextTableBuilder) -> None:
        self._tables = tables

    def build(self, request: ExtractionRequest, slides: Sequence[PptxSlide]) -> ParsedDocument:
        """Build the result for a presentation.

        Args:
            request: The file, its facts and its detection.
            slides: The slides in presentation order.

        Returns:
            The parsed document.
        """
        located = [(slide.number, block) for slide in slides for block in slide.blocks]
        elements = tuple(
            self._element(n, slide, block) for n, (slide, block) in enumerate(located, 1)
        )
        unreadable = tuple(
            ParseWarning(WarningCode.SLIDE_UNREADABLE, Locator.for_slide(slide.number))
            for slide in slides
            if not slide.readable
        )
        return ParsedDocument(
            status=DocumentStatus.PARTIAL if unreadable else DocumentStatus.SUCCEEDED,
            facts=dataclasses.replace(request.facts, slide_count=len(slides)),
            elements=elements,
            warnings=request.detection.warnings + unreadable,
            outline=tuple(self._outline(slides)),
            metrics=Metrics.for_elements(elements, self._counts(slides, elements)),
        )

    def _element(self, position: int, slide: int, block: SlideBlock) -> Element:
        locator = Locator.for_slide(slide)
        level = 1 if block.kind is ElementKind.HEADING else None
        table = None
        if block.kind is ElementKind.TABLE:
            table = self._tables.build(block.rows, header_marked=block.header_marked)
        return Element(ElementId.at(position), block.kind, locator, block.text, level, table)

    @staticmethod
    def _outline(slides: Sequence[PptxSlide]) -> Iterator[OutlineEntry]:
        for slide in slides:
            name = slide.title or f"Slide {slide.number}"
            yield OutlineEntry(OutlineKind.SLIDE, name, Locator.for_slide(slide.number))

    @staticmethod
    def _counts(slides: Sequence[PptxSlide], elements: Sequence[Element]) -> dict[MetricName, int]:
        words = sum(len(element.text.split()) for element in elements if element.text)
        return {MetricName.SLIDES: len(slides), MetricName.WORDS: words}
