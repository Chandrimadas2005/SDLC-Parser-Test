from pathlib import Path
import json

import pytest

pytest.importorskip("xlrd")

from ParserService.Domain.Documents import DetectedType, Detection, DocumentFacts, ExtractionRequest, ParsedDocument, SourceFile
from ParserService.Domain.Jobs import FileHash, FileName
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
from ParserService.Infrastructure.Extraction.XlsExtractor import XlsExtractor
from ParserService.Infrastructure.Output.ParsedDocumentJsonEncoder import ParsedDocumentJsonEncoder


class TestXlsExtractor:
    """Tests legacy XLS extraction against synthetic workbook fixtures."""

    ROOT = Path(__file__).parents[2] / "corpus" / "xls"

    def _request(self, path: Path, name: str | None = None) -> ExtractionRequest:
        file_name = FileName(name or path.name)
        facts = DocumentFacts(file_name, DetectedType.XLS, path.stat().st_size, FileHash.of(path.read_bytes()))
        return ExtractionRequest(SourceFile(str(path), file_name), facts, Detection(DetectedType.XLS, None, ()))

    def test_reads_legacy_table_and_expands_merged_cells(self) -> None:
        path = self.ROOT / "normal" / "normal.xls"
        document = XlsExtractor(SpreadsheetTableBuilder()).extract(self._request(path)).unwrap()
        table = document.elements[0].table
        assert table is not None
        assert table.header_row == 1
        assert table.rows[0].cells["Total"] == "4.0"
        assert table.rows[2].cells["Record ID"] == "REC-002"
        self._golden(document, "xls_normal.json")

    def test_includes_hidden_sheet_outline(self) -> None:
        path = self.ROOT / "hidden" / "hidden.xls"
        document = XlsExtractor(SpreadsheetTableBuilder()).extract(self._request(path)).unwrap()
        assert any(entry.hidden for entry in document.outline)

    def test_corrupted_xls_returns_failure(self) -> None:
        path = self.ROOT / "corrupted" / "corrupted.xls"
        result = XlsExtractor(SpreadsheetTableBuilder()).extract(self._request(path))
        assert result.unwrap_err().value == "corrupted_file"
        expected = json.loads((Path(__file__).parents[2] / "golden" / "extraction" / "xls_corrupted.json").read_text())
        assert expected["failure_reason"] == result.unwrap_err().value

    def _golden(self, document: ParsedDocument, name: str) -> None:
        path = Path(__file__).parents[2] / "golden" / "extraction" / name
        assert ParsedDocumentJsonEncoder().to_json(document) == path.read_text(encoding="utf-8")
