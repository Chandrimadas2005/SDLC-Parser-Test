from pathlib import Path

from ParserService.Domain.Documents import (
    DetectedType,
    Detection,
    DocumentFacts,
    ExtractionRequest,
    ParsedDocument,
    SourceFile,
)
from ParserService.Domain.Jobs import FileHash, FileName
from ParserService.Infrastructure.Extraction.CsvExtractor import CsvExtractor
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
from ParserService.Infrastructure.Extraction.TsvExtractor import TsvExtractor
from ParserService.Infrastructure.Output.ParsedDocumentJsonEncoder import ParsedDocumentJsonEncoder


class TestDelimitedSpreadsheetExtractors:
    """Tests CSV and TSV parsing with synthetic corpus files."""

    ROOT = Path(__file__).parents[2] / "corpus"

    def _request(self, path: Path, detected_type: DetectedType) -> ExtractionRequest:
        name = FileName(path.name)
        facts = DocumentFacts(
            name, detected_type, path.stat().st_size, FileHash.of(path.read_bytes())
        )
        return ExtractionRequest(
            SourceFile(str(path), name), facts, Detection(detected_type, "utf-8", ())
        )

    def test_csv_extracts_header_rows_and_profiles(self) -> None:
        path = self.ROOT / "csv" / "normal" / "records.csv"
        document = (
            CsvExtractor(SpreadsheetTableBuilder())
            .extract(self._request(path, DetectedType.CSV))
            .unwrap()
        )
        table = document.elements[0].table
        assert table is not None
        assert table.header_row == 1
        assert table.rows[0].row == 2
        assert table.rows[0].cells["Record ID"] == "REC-001"
        assert table.column_profiles[1].guessed_type.value == "number"
        assert document.elements[0].locator.cell_range == "A1:C3"
        self._golden(document, "csv_records.json")

    def test_tsv_uses_tab_delimiter(self) -> None:
        path = self.ROOT / "tsv" / "normal" / "records.tsv"
        document = (
            TsvExtractor(SpreadsheetTableBuilder())
            .extract(self._request(path, DetectedType.TSV))
            .unwrap()
        )
        table = document.elements[0].table
        assert table is not None
        assert table.rows[1].cells["Status"] == "valid"
        assert document.elements[0].locator.cell_range == "A1:C3"
        self._golden(document, "tsv_records.json")

    def test_empty_csv_returns_empty_table(self) -> None:
        path = self.ROOT / "csv" / "empty" / "empty.csv"
        document = (
            CsvExtractor(SpreadsheetTableBuilder())
            .extract(self._request(path, DetectedType.CSV))
            .unwrap()
        )
        table = document.elements[0].table
        assert table is not None
        assert table.rows == ()
        self._golden(document, "csv_empty.json")

    def _golden(self, document: ParsedDocument, name: str) -> None:
        path = Path(__file__).parents[2] / "golden" / "extraction" / name
        assert ParsedDocumentJsonEncoder().to_json(document) == path.read_text(encoding="utf-8")
