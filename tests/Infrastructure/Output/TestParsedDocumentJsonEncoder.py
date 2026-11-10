import dataclasses
import json
from pathlib import Path

import pytest

from ParserService.Domain.Documents import ParsedDocument
from ParserService.Infrastructure.Output import ParsedDocumentJsonEncoder
from tests.Samples import DocumentSamples


class TestParsedDocumentJsonEncoder:
    """The JSON form matches the golden files byte for byte."""

    GOLDEN = Path(__file__).resolve().parents[2] / "golden" / "output"
    SAMPLES = DocumentSamples()
    ENCODER = ParsedDocumentJsonEncoder()

    @pytest.mark.parametrize(
        ("sample_name", "document"),
        [
            ("text_document", SAMPLES.text_document()),
            ("spreadsheet", SAMPLES.spreadsheet()),
            ("failed", SAMPLES.failed()),
        ],
    )
    def test_output_matches_golden_file(self, sample_name: str, document: ParsedDocument) -> None:
        expected = (self.GOLDEN / f"{sample_name}.json").read_text(encoding="utf-8")

        assert self.ENCODER.to_json(document) == expected

    def test_output_is_stable_and_keeps_non_ascii_text(self) -> None:
        document = self.SAMPLES.text_document()
        element = dataclasses.replace(document.elements[1], text="naïve café")
        changed = dataclasses.replace(document, elements=(document.elements[0], element))

        first, second = self.ENCODER.to_json(changed), self.ENCODER.to_json(changed)

        assert first == second
        assert "naïve café" in first
        assert json.loads(first) == self.ENCODER.encode(changed)
