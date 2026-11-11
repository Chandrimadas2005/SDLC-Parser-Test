from pathlib import Path
import json

from ParserService.Domain.Documents import (
    DetectedType,
    Detection,
    DocumentFacts,
    ExtractionRequest,
    ParsedDocument,
    SourceFile,
    WarningCode,
)
from ParserService.Domain.Jobs import FileHash, FileName
from ParserService.Infrastructure.Extraction import SpreadsheetTableBuilder, XlsxExtractor
from ParserService.Infrastructure.Output.ParsedDocumentJsonEncoder import ParsedDocumentJsonEncoder


class TestXlsxExtractor:
    """Contract tests for streaming XLSX extraction."""

    ROOT = Path(__file__).parents[2] / "corpus" / "xlsx"

    def _request(self, path: Path, name: str = "normal.xlsx") -> ExtractionRequest:
        facts = DocumentFacts(
            FileName(name), DetectedType.XLSX, path.stat().st_size, FileHash.of(path.read_bytes())
        )
        return ExtractionRequest(SourceFile(str(path), facts.file_name), facts, Detection(DetectedType.XLSX, None, ()))

    def test_extracts_tables_formulas_and_expands_merged_cells(self) -> None:
        path = self.ROOT / "normal" / "normal.xlsx"
        result = XlsxExtractor(SpreadsheetTableBuilder()).extract(self._request(path))
        document = result.unwrap()
        assert len(document.elements) == 2
        table = document.elements[0].table
        assert table is not None
        assert table.header_row == 1
        assert table.rows[0].cells["Total"].formula == "=SUM(B2:B2)"
        assert table.rows[1].cells["Record ID"] == "REC-002"
        assert document.elements[0].locator.cell_range == "A1:C4"
        assert document.metrics.counts[next(name for name in document.metrics.counts if name.value == "formulas")] == 1
        self._golden(document, "xlsx_normal.json")

    def test_keeps_hidden_sheet_in_outline(self) -> None:
        path = self.ROOT / "hidden" / "hidden.xlsx"
        document = XlsxExtractor(SpreadsheetTableBuilder()).extract(self._request(path, "hidden.xlsx")).unwrap()
        assert document.outline[0].hidden is True
        self._golden(document, "xlsx_hidden.json")

    def test_empty_workbook_returns_a_defined_document(self) -> None:
        path = self.ROOT / "empty" / "empty.xlsx"
        document = XlsxExtractor(SpreadsheetTableBuilder()).extract(self._request(path, "empty.xlsx")).unwrap()
        assert document.status.value == "succeeded"
        self._golden(document, "xlsx_empty.json")

    def test_corrupted_workbook_returns_corrupted_file(self) -> None:
        path = self.ROOT / "corrupted" / "corrupted.xlsx"
        result = XlsxExtractor(SpreadsheetTableBuilder()).extract(self._request(path, "corrupted.xlsx"))
        assert result.unwrap_err().value == "corrupted_file"
        expected = json.loads((Path(__file__).parents[2] / "golden" / "extraction" / "xlsx_corrupted.json").read_text())
        assert expected["failure_reason"] == result.unwrap_err().value


    def test_one_unreadable_sheet_keeps_other_sheets_and_marks_partial(self) -> None:
        path = self.ROOT / "partial-corrupt" / "partial.xlsx"
        document = XlsxExtractor(SpreadsheetTableBuilder()).extract(self._request(path, "partial.xlsx")).unwrap()
        assert document.status.value == "partial"
        assert len(document.elements) == 2
        assert any(warning.code is WarningCode.SHEET_UNREADABLE for warning in document.warnings)
        assert document.warnings[-1].locator is not None
        self._golden(document, "xlsx_partial.json")

    def test_wrong_extension_still_reads_workbook(self) -> None:
        path = self.ROOT / "wrong-extension" / "normal.txt"
        document = XlsxExtractor(SpreadsheetTableBuilder()).extract(self._request(path, "normal.txt")).unwrap()
        assert len(document.elements) == 2
        self._golden(document, "xlsx_wrong_extension.json")

    def _golden(self, document: ParsedDocument, name: str) -> None:
        path = Path(__file__).parents[2] / "golden" / "extraction" / name
        assert ParsedDocumentJsonEncoder().to_json(document) == path.read_text(encoding="utf-8")
