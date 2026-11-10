from ParserService.Domain.Documents import (
    Confidence,
    DetectedType,
    DocumentFacts,
    DocumentStatus,
    Element,
    ElementId,
    ElementKind,
    Locator,
    MetricName,
    Metrics,
    OutlineEntry,
    OutlineKind,
    ParsedDocument,
    ParseWarning,
    Table,
    TableRow,
    WarningCode,
)
from ParserService.Domain.Jobs import FailureReason, FileHash, FileName


class DocumentSamples:
    """Builds small synthetic ``ParsedDocument`` values for tests."""

    def facts(self, detected_type: DetectedType) -> DocumentFacts:
        """File facts for a tiny synthetic file of the given type."""
        return DocumentFacts(
            file_name=FileName(f"sample.{detected_type}"),
            detected_type=detected_type,
            size_bytes=42,
            sha256=FileHash.of(b"synthetic"),
            properties={"title": "Synthetic sample"},
        )

    def text_document(self) -> ParsedDocument:
        """A succeeded text document with a heading and a paragraph."""
        body = Locator.for_text(2, 7, 18)
        elements = (
            Element(ElementId.at(1), ElementKind.HEADING, Locator.for_text(1, 0, 5), "Intro", 1),
            Element(ElementId.at(2), ElementKind.PARAGRAPH, body, "Hello there"),
        )
        outline = (OutlineEntry(OutlineKind.HEADING, "Intro", Locator.for_text(1, 0, 5), 1),)
        return ParsedDocument(
            status=DocumentStatus.SUCCEEDED,
            facts=self.facts(DetectedType.MD),
            elements=elements,
            warnings=(),
            outline=outline,
            metrics=Metrics.for_elements(elements, {MetricName.WORDS: 3}),
        )

    def spreadsheet(self) -> ParsedDocument:
        """A partial spreadsheet with one table and one unreadable sheet."""
        row = TableRow(2, {"ID": "REQ-0412", "Statement": "Synthetic statement"})
        table = Table(rows=(row,), header_row=1, header_confidence=Confidence(0.92))
        locator = Locator.for_cells("Requirements", "A1:B2")
        archive = Locator.for_cells("Archive", None)
        elements = (Element(ElementId.at(1), ElementKind.TABLE, locator, table=table),)
        return ParsedDocument(
            status=DocumentStatus.PARTIAL,
            facts=self.facts(DetectedType.XLSX),
            elements=elements,
            warnings=(ParseWarning(WarningCode.SHEET_UNREADABLE, archive),),
            outline=(OutlineEntry(OutlineKind.SHEET, "Requirements", locator),),
            metrics=Metrics.for_elements(elements, {MetricName.ROWS: 1, MetricName.COLUMNS: 2}),
        )

    def failed(self) -> ParsedDocument:
        """A failed result with its reason and a whole-file warning."""
        return ParsedDocument(
            status=DocumentStatus.FAILED,
            facts=self.facts(DetectedType.PDF),
            elements=(),
            warnings=(ParseWarning(WarningCode.EXTENSION_MISMATCH),),
            outline=(),
            metrics=Metrics.for_elements((), {}),
            failure_reason=FailureReason.PASSWORD_PROTECTED,
        )
