import json
from pathlib import Path
from typing import Final

from jsonschema import Draft202012Validator

from ParserService.Domain.Documents import (
    DocumentStatus,
    ElementKind,
    ParsedDocument,
    SourceFile,
    WarningCode,
)
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import ExtractorRegistry, ParsePipeline
from ParserService.Infrastructure.Output import ParsedDocumentJsonEncoder
from tests.Samples import SamplePptx

ROOT: Final = Path(__file__).resolve().parents[3]
GOLDEN: Final = ROOT / "tests" / "golden" / "extraction"
SCHEMA: Final = ROOT / "schemas" / "parsed_document.v1.json"


class TestPptxExtractor:
    """Slides give titles, bullets, tables and image alt text, each located by slide."""

    PIPELINE = ParsePipeline(
        MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
        ExtractorRegistry.default(),
    )
    SAMPLES = SamplePptx()

    def _parse(self, path: Path) -> Result[ParsedDocument, FailureReason]:
        return self.PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

    def test_normal_pptx_matches_its_golden_file(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "deck.pptx")).unwrap()

        expected = (GOLDEN / "pptx_normal.json").read_text(encoding="utf-8")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        assert ParsedDocumentJsonEncoder().to_json(document) == expected
        Draft202012Validator(schema).validate(json.loads(expected))

    def test_slides_keep_their_structure_and_order(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "deck.pptx")).unwrap()

        found = [(e.kind, e.text, e.locator.slide) for e in document.elements]
        assert found == [
            (ElementKind.HEADING, "Synthetic deck", 1),
            (ElementKind.LIST_ITEM, "First point", 1),
            (ElementKind.LIST_ITEM, "Second point", 1),
            (ElementKind.PARAGRAPH, "Free text box", 1),
            (ElementKind.HEADING, "Numbers", 2),
            (ElementKind.TABLE, None, 2),
            (ElementKind.IMAGE, "Synthetic chart", 2),
        ]
        assert [entry.name for entry in document.outline] == [
            "Synthetic deck",
            "Numbers",
            "Slide 3",
        ]

    def test_broken_slide_makes_the_result_partial(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "deck.pptx")).unwrap()

        assert document.status is DocumentStatus.PARTIAL
        assert document.facts.slide_count == 3
        assert [w.code for w in document.warnings] == [WarningCode.SLIDE_UNREADABLE]
        assert document.warnings[0].locator is not None
        assert document.warnings[0].locator.slide == 3

    def test_marked_header_row_names_the_columns(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "deck.pptx")).unwrap()
        table = next(e.table for e in document.elements if e.table is not None)

        assert table.header_row == 1
        assert table.rows[0].cells == {"Metric": "Pages", "Value": "12"}

    def test_empty_and_corrupted_presentations(self, tmp_path: Path) -> None:
        empty = self._parse(self.SAMPLES.empty(tmp_path / "empty.pptx")).unwrap()
        broken = self._parse(self.SAMPLES.corrupted(tmp_path / "broken.pptx"))

        assert empty.elements == ()
        assert empty.status is DocumentStatus.SUCCEEDED
        assert broken.unwrap_err() is FailureReason.CORRUPTED_FILE
