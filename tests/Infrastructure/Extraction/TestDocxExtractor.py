import json
from pathlib import Path
from typing import Final

from jsonschema import Draft202012Validator

from ParserService.Domain.Documents import ElementKind, ParsedDocument, SourceFile
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import DocxProperty, ExtractorRegistry, ParsePipeline
from ParserService.Infrastructure.Output import ParsedDocumentJsonEncoder
from tests.Samples import SampleDocx

GOLDEN: Final = Path(__file__).resolve().parents[2] / "golden" / "extraction"
SCHEMA: Final = Path(__file__).resolve().parents[3] / "schemas" / "parsed_document.v1.json"


class TestDocxExtractor:
    """Word files give headings, lists, tables, comments and accepted tracked changes."""

    PIPELINE = ParsePipeline(
        MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
        ExtractorRegistry.default(),
    )
    SAMPLES = SampleDocx()

    def _parse(self, path: Path) -> Result[ParsedDocument, FailureReason]:
        return self.PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

    def test_normal_docx_matches_its_golden_file(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "report.docx")).unwrap()

        expected = (GOLDEN / "docx_normal.json").read_text(encoding="utf-8")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        assert ParsedDocumentJsonEncoder().to_json(document) == expected
        Draft202012Validator(schema).validate(json.loads(expected))

    def test_headings_lists_and_comments_keep_their_structure(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "report.docx")).unwrap()

        kinds = [(element.kind, element.text, element.level) for element in document.elements]
        assert kinds[:6] == [
            (ElementKind.HEADING, "Synthetic report", 1),
            (ElementKind.HEADING, "Introduction", 1),
            (ElementKind.PARAGRAPH, "Kept text and inserted.", None),
            (ElementKind.COMMENT, "Synthetic reviewer note", None),
            (ElementKind.LIST_ITEM, "First bullet", None),
            (ElementKind.LIST_ITEM, "Numbered item", None),
        ]
        assert [entry.name for entry in document.outline] == [
            "Synthetic report",
            "Introduction",
            "Details",
        ]

    def test_tracked_changes_are_accepted_and_counted(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "report.docx")).unwrap()

        texts = " ".join(element.text or "" for element in document.elements)
        properties = document.facts.properties or {}
        assert "deleted" not in texts
        assert properties[DocxProperty.TRACKED_INSERTIONS] == "1"
        assert properties[DocxProperty.TRACKED_DELETIONS] == "1"

    def test_tables_detect_marked_and_guessed_headers(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "report.docx")).unwrap()
        marked, unmarked = (e.table for e in document.elements if e.table is not None)

        assert marked is not None
        assert unmarked is not None
        assert marked.header_row == 1
        assert marked.rows[0].cells == {"ID": "REQ-1", "Owner": "Team A"}
        assert unmarked.header_row is None
        assert unmarked.rows[0].cells == {"Column 1": "a", "Column 2": "a"}

    def test_empty_and_corrupted_documents(self, tmp_path: Path) -> None:
        empty = self._parse(self.SAMPLES.empty(tmp_path / "empty.docx")).unwrap()
        broken = self._parse(self.SAMPLES.corrupted(tmp_path / "broken.docx"))

        assert empty.elements == ()
        assert broken.unwrap_err() is FailureReason.CORRUPTED_FILE
