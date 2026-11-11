from ParserService.Domain.Documents import (
    DetectedType,
    Detection,
    DocumentFacts,
    ExtractionRequest,
    SourceFile,
)
from ParserService.Domain.Jobs import FileHash, FileName
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder


class TestSpreadsheetTableBuilder:
    """Tests spreadsheet header and column-profile inference."""

    def test_profiles_infer_types_fill_and_unique_counts(self) -> None:
        name = FileName("sample.xlsx")
        facts = DocumentFacts(name, DetectedType.XLSX, 1, FileHash.of(b"x"))
        request = ExtractionRequest(SourceFile("/synthetic.xlsx", name), facts, Detection(DetectedType.XLSX, None, ()))
        rows = [["ID", "Amount", "Active"], ["A-0001", "12", "true"], ["A-0002", "", "false"]]
        document = SpreadsheetTableBuilder().build(request, [("Sheet1", False, rows)], 0)
        profiles = document.elements[0].table.column_profiles
        assert document.elements[0].table.header_row == 1
        assert profiles[0].looks_like_id is True
        assert profiles[2].looks_like_id is False
        assert profiles[1].guessed_type.value == "number"
        assert profiles[1].fill_rate == 0.5
        assert profiles[1].unique_values == 1
        assert profiles[2].guessed_type.value == "boolean"
