import dataclasses
from collections.abc import Iterator

from ParserService.Domain.Documents.DocumentFacts import DocumentFacts
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
from ParserService.Infrastructure.Extraction.DocxContent import DocxContent
from ParserService.Infrastructure.Extraction.DocxParagraph import DocxParagraph
from ParserService.Infrastructure.Extraction.DocxProperty import DocxProperty
from ParserService.Infrastructure.Extraction.DocxTable import DocxTable
from ParserService.Infrastructure.Extraction.TextTableBuilder import TextTableBuilder

type _Draft = tuple[ElementKind, Locator, str | None, int | None, Table | None]


class DocxDocumentAssembler:
    """Turns DOCX content into a ``ParsedDocument``.

    Each body block keeps its position as the paragraph number in its locator, so
    empty paragraphs still count. Comments follow the paragraph they are anchored to.
    Tracked-change counts go into the file properties.
    """

    def __init__(self, tables: TextTableBuilder) -> None:
        self._tables = tables

    def build(self, request: ExtractionRequest, content: DocxContent) -> ParsedDocument:
        """Build the result for a DOCX file.

        Args:
            request: The file, its facts and its detection.
            content: Blocks, comments and tracked changes read from the file.

        Returns:
            A succeeded ``ParsedDocument``.
        """
        drafts = list(self._drafts(content))
        elements = tuple(
            Element(ElementId.at(n), kind, locator, text, level, table)
            for n, (kind, locator, text, level, table) in enumerate(drafts, 1)
        )
        words = sum(len(element.text.split()) for element in elements if element.text)
        return ParsedDocument(
            status=DocumentStatus.SUCCEEDED,
            facts=self._facts(request, content),
            elements=elements,
            warnings=request.detection.warnings,
            outline=self._outline(elements),
            metrics=Metrics.for_elements(elements, {MetricName.WORDS: words}),
        )

    def _drafts(self, content: DocxContent) -> Iterator[_Draft]:
        for number, block in enumerate(content.blocks, 1):
            if isinstance(block, DocxTable):
                yield (
                    ElementKind.TABLE,
                    Locator(paragraph=number),
                    None,
                    None,
                    self._tables.build(block.rows, header_marked=block.header_marked),
                )
                continue
            yield from self._paragraph(block, number)
            for comment_id in block.comment_ids:
                text = content.comments.get(comment_id)
                yield ElementKind.COMMENT, Locator(paragraph=number), text, None, None

    @staticmethod
    def _paragraph(block: DocxParagraph, number: int) -> Iterator[_Draft]:
        if not block.text:
            return
        locator = Locator.for_text(number, 0, len(block.text))
        if block.level is not None:
            yield ElementKind.HEADING, locator, block.text, block.level, None
            return
        kind = ElementKind.LIST_ITEM if block.is_list else ElementKind.PARAGRAPH
        yield kind, locator, block.text, None, None

    @staticmethod
    def _outline(elements: tuple[Element, ...]) -> tuple[OutlineEntry, ...]:
        return tuple(
            OutlineEntry(OutlineKind.HEADING, element.text, element.locator, element.level)
            for element in elements
            if element.kind is ElementKind.HEADING and element.text
        )

    @staticmethod
    def _facts(request: ExtractionRequest, content: DocxContent) -> DocumentFacts:
        changes = {
            DocxProperty.TRACKED_INSERTIONS: content.insertions,
            DocxProperty.TRACKED_DELETIONS: content.deletions,
        }
        tracked = {str(key): str(count) for key, count in changes.items() if count}
        merged = {**(request.facts.properties or {}), **tracked}
        return dataclasses.replace(request.facts, properties=merged or request.facts.properties)
