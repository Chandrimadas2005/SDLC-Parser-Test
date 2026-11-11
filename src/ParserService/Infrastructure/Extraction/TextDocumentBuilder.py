from collections.abc import Sequence

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
from ParserService.Infrastructure.Extraction.TextBlock import TextBlock


class TextDocumentBuilder:
    """Turns the blocks of a text file into a ``ParsedDocument``.

    Each block becomes one element whose locator is its block number (as the
    paragraph) and its character span. Headings also become outline entries.
    Detection warnings, such as a guessed encoding, are carried into the result.
    """

    def build(self, request: ExtractionRequest, blocks: Sequence[TextBlock]) -> ParsedDocument:
        """Build the result for a text file.

        Args:
            request: The file, its facts and its detection.
            blocks: The blocks found in reading order.

        Returns:
            A succeeded ``ParsedDocument``.
        """
        located = [(Locator.for_text(n, b.start, b.end), b) for n, b in enumerate(blocks, 1)]
        elements = tuple(
            Element(ElementId.at(n), block.kind, locator, block.content, block.level)
            for n, (locator, block) in enumerate(located, 1)
        )
        words = sum(len(block.content.split()) for block in blocks)
        return ParsedDocument(
            status=DocumentStatus.SUCCEEDED,
            facts=request.facts,
            elements=elements,
            warnings=request.detection.warnings,
            outline=self._outline(located),
            metrics=Metrics.for_elements(elements, {MetricName.WORDS: words}),
        )

    @staticmethod
    def _outline(located: Sequence[tuple[Locator, TextBlock]]) -> tuple[OutlineEntry, ...]:
        return tuple(
            OutlineEntry(OutlineKind.HEADING, block.content, locator, block.level)
            for locator, block in located
            if block.kind is ElementKind.HEADING
        )
