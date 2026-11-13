import json
from pathlib import Path
from typing import Final

import pytest
from jsonschema import Draft202012Validator

from ParserService.Domain.Documents import DetectedType, ParsedDocument, SourceFile, WarningCode
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Extraction import ExtractorRegistry, ParsePipeline
from ParserService.Infrastructure.Output import ParsedDocumentJsonEncoder

TESTS: Final = Path(__file__).resolve().parents[2]
CORPUS: Final = TESTS / "corpus"
GOLDEN: Final = TESTS / "golden" / "extraction"
SCHEMA: Final = json.loads(
    (TESTS.parent / "schemas" / "parsed_document.v1.json").read_text(encoding="utf-8")
)
GOLDENS: Final = [
    ("html/normal/synthetic.html", "html_synthetic"),
    ("html/normal/article.html", "html_article"),
    ("html/malformed/broken.html", "html_malformed"),
    ("html/empty/empty.html", "html_empty"),
    ("html/wrong-extension/page.txt", "html_wrong_extension"),
    ("ods/normal/normal.ods", "ods_normal"),
    ("ods/hidden/hidden.ods", "ods_hidden"),
    ("ods/empty/empty.ods", "ods_empty"),
    ("ods/partial-corrupt/partial.ods", "ods_partial"),
    ("ods/wrong-extension/normal.xlsx", "ods_wrong_extension"),
]


class TestHtmlAndOdsCorpus:
    """Every HTML and ODS corpus file parses into its golden, schema-valid result."""

    PIPELINE = ParsePipeline.default()
    ENCODER = ParsedDocumentJsonEncoder()
    VALIDATOR = Draft202012Validator(SCHEMA)

    def _parse(self, path: Path) -> ParsedDocument:
        return self.PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()

    @pytest.mark.parametrize(("relative", "golden"), GOLDENS)
    def test_corpus_file_matches_its_golden_file(self, relative: str, golden: str) -> None:
        encoded = self.ENCODER.to_json(self._parse(CORPUS / relative))

        assert encoded == (GOLDEN / f"{golden}.json").read_text(encoding="utf-8")
        self.VALIDATOR.validate(json.loads(encoded))

    @pytest.mark.parametrize(
        "relative", ["html/wrong-extension/page.txt", "ods/wrong-extension/normal.xlsx"]
    )
    def test_a_wrong_extension_parses_by_content_and_warns(self, relative: str) -> None:
        document = self._parse(CORPUS / relative)

        assert document.warnings[0].code is WarningCode.EXTENSION_MISMATCH

    def test_a_truncated_spreadsheet_fails_as_corrupted_not_unsupported(self) -> None:
        path = CORPUS / "ods" / "corrupted" / "truncated.ods"

        result = self.PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE

    def test_an_html_fragment_named_html_is_parsed_as_html(self, tmp_path: Path) -> None:
        path = tmp_path / "fragment.html"
        path.write_text("Just a <b>fragment</b>.\n", encoding="utf-8")

        document = self._parse(path)

        assert document.facts.detected_type is DetectedType.HTML
        assert [element.text for element in document.elements] == ["Just a fragment."]

    def test_html_and_ods_are_always_registered(self) -> None:
        supported = ExtractorRegistry.default().supported_types

        assert DetectedType.HTML in supported
        assert DetectedType.ODS in supported
