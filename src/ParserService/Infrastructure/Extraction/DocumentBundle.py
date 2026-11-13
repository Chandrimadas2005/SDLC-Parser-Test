import dataclasses
from collections.abc import Iterator, Sequence

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
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Infrastructure.Extraction.BundleSection import BundleSection


class DocumentBundle:
    """Joins the results of a container's parts (archive entries, e-mail parts) into one.

    Every part starts with a level-1 heading carrying its title, located by the
    part's position as paragraph N; the part's own elements follow with their own
    locators (pages, sheets, slides inside that part). A part that failed adds
    ``element_skipped`` at its position, and any failed or partial part makes the
    whole result ``partial``.
    """

    def build(
        self, request: ExtractionRequest, sections: Sequence[BundleSection]
    ) -> ParsedDocument:
        """Build the combined result.

        Args:
            request: The container file, its facts and its detection.
            sections: The parts, in their order inside the container.

        Returns:
            One parsed document for the whole container.
        """
        elements = tuple(
            dataclasses.replace(element, element_id=ElementId.at(n))
            for n, element in enumerate(self._elements(sections), 1)
        )
        skipped = tuple(self._skipped(sections))
        words = sum(len(element.text.split()) for element in elements if element.text)
        return ParsedDocument(
            status=DocumentStatus.PARTIAL if skipped else DocumentStatus.SUCCEEDED,
            facts=self._facts(request.facts, sections),
            elements=elements,
            warnings=request.detection.warnings + skipped,
            outline=tuple(self._outline(sections)),
            metrics=Metrics.for_elements(elements, {MetricName.WORDS: words}),
        )

    @staticmethod
    def _elements(sections: Sequence[BundleSection]) -> Iterator[Element]:
        for number, section in enumerate(sections, 1):
            locator = Locator(paragraph=number)
            yield Element(ElementId.at(1), ElementKind.HEADING, locator, section.title, 1)
            if section.document.is_ok:
                yield from section.document.unwrap().elements

    @staticmethod
    def _skipped(sections: Sequence[BundleSection]) -> Iterator[ParseWarning]:
        for number, section in enumerate(sections, 1):
            result = section.document
            if result.is_err or result.unwrap().status is not DocumentStatus.SUCCEEDED:
                yield ParseWarning(WarningCode.ELEMENT_SKIPPED, Locator(paragraph=number))

    @staticmethod
    def _outline(sections: Sequence[BundleSection]) -> Iterator[OutlineEntry]:
        for number, section in enumerate(sections, 1):
            yield OutlineEntry(OutlineKind.HEADING, section.title, Locator(paragraph=number), 1)

    @staticmethod
    def _facts(facts: DocumentFacts, sections: Sequence[BundleSection]) -> DocumentFacts:
        parts = {"embedded_parts": str(len(sections))}
        return dataclasses.replace(facts, properties={**(facts.properties or {}), **parts})
