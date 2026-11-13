from dataclasses import replace

from ParserService.Domain.Documents import (
    Element,
    ElementId,
    ElementKind,
    Locator,
    Metrics,
    OutlineEntry,
    OutlineKind,
    ParsedDocument,
)
from ParserService.Infrastructure.Summary import ExtractiveSummaryGenerator
from tests.Samples import DocumentSamples


class TestExtractiveSummaryGenerator:
    """The summary works for every format, because it reads only the ParsedDocument."""

    GENERATOR = ExtractiveSummaryGenerator()

    def _summary(self, document: ParsedDocument) -> str:
        return self.GENERATOR.generate(document).unwrap().text

    def test_a_text_document_is_summarised_from_its_outline_and_opening(self) -> None:
        text = self._summary(DocumentSamples().text_document())

        assert text.splitlines() == [
            "sample.md (MD, 42 bytes) parsed as succeeded"
            " with 2 elements (1 heading, 1 paragraph).",
            "Outline: Intro.",
            "Counts: words 3.",
            "Opening text: Hello there",
        ]

    def test_a_spreadsheet_is_summarised_from_its_sheets_counts_and_warnings(self) -> None:
        text = self._summary(DocumentSamples().spreadsheet())

        assert "(XLSX, 42 bytes) parsed as partial with 1 elements (1 table)." in text
        assert "Outline: Requirements." in text
        assert "Counts: rows 1, columns 3, formulas 1." in text
        assert "Warnings: sheet_unreadable." in text
        assert "Opening text" not in text

    def test_a_document_without_elements_still_gets_a_summary(self) -> None:
        text = self._summary(DocumentSamples().failed())

        assert "parsed as failed with no elements." in text
        assert "Warnings: extension_mismatch." in text

    def test_long_outlines_and_openings_are_shortened(self) -> None:
        document = self._long_document()

        lines = self._summary(document).splitlines()

        assert lines[1].endswith("h7; h8 (and 2 more).")
        opening = lines[-1].removeprefix("Opening text: ")
        assert opening.endswith("...")
        assert len(opening) <= ExtractiveSummaryGenerator.MAX_OPENING_CHARACTERS + 3

    def test_repeated_warning_codes_are_tallied(self) -> None:
        document = DocumentSamples().spreadsheet()
        twice = replace(document, warnings=document.warnings * 2)

        assert "Warnings: sheet_unreadable x2." in self._summary(twice)

    def test_the_same_document_always_gives_the_same_summary(self) -> None:
        document = DocumentSamples().spreadsheet()

        assert self._summary(document) == self._summary(document)

    @staticmethod
    def _long_document() -> ParsedDocument:
        locator = Locator.for_text(1, 0, 1)
        outline = tuple(
            OutlineEntry(OutlineKind.HEADING, f"h{n}", locator, 1) for n in range(1, 11)
        )
        paragraph = Element(ElementId.at(1), ElementKind.PARAGRAPH, locator, "word " * 200)
        base = DocumentSamples().text_document()
        metrics = Metrics.for_elements((paragraph,), {})
        return replace(base, elements=(paragraph,), outline=outline, metrics=metrics)
