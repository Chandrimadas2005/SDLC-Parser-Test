import json
from enum import StrEnum
from pathlib import Path
from typing import Final

import pytest
from jsonschema import Draft202012Validator

from ParserService.Domain.Documents import (
    DetectedType,
    DocumentStatus,
    ElementKind,
    MetricName,
    OutlineKind,
    ParsedDocument,
    WarningCode,
)
from ParserService.Domain.Jobs import FailureReason
from ParserService.Infrastructure.Output import OutputField, ParsedDocumentJsonEncoder
from tests.Contract.SchemaKeyword import SchemaKeyword
from tests.Samples import DocumentSamples

SCHEMA_PATH: Final = Path(__file__).resolve().parents[2] / "schemas" / "parsed_document.v1.json"
SAMPLES: Final = DocumentSamples()


class TestParsedDocumentSchema:
    """The JSON Schema in the repository and the encoder output never drift apart."""

    SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    VALIDATOR = Draft202012Validator(SCHEMA)
    ENCODER = ParsedDocumentJsonEncoder()
    ENUMS: Final[dict[SchemaKeyword, type[StrEnum]]] = {
        SchemaKeyword.STATUS: DocumentStatus,
        SchemaKeyword.DETECTED_TYPE: DetectedType,
        SchemaKeyword.ELEMENT_KIND: ElementKind,
        SchemaKeyword.OUTLINE_KIND: OutlineKind,
        SchemaKeyword.WARNING_CODE: WarningCode,
        SchemaKeyword.FAILURE_REASON: FailureReason,
        SchemaKeyword.METRIC_NAME: MetricName,
    }

    def test_schema_is_a_valid_draft_2020_12_schema(self) -> None:
        Draft202012Validator.check_schema(self.SCHEMA)

    def test_schema_version_matches_the_model(self) -> None:
        version = self.SCHEMA[SchemaKeyword.PROPERTIES][OutputField.SCHEMA_VERSION]

        assert version[SchemaKeyword.CONST] == ParsedDocument.SCHEMA_VERSION

    @pytest.mark.parametrize("definition", list(ENUMS))
    def test_schema_enums_match_the_model_enums(self, definition: SchemaKeyword) -> None:
        allowed = self.SCHEMA[SchemaKeyword.DEFS][definition][SchemaKeyword.ENUM]

        assert allowed == [member.value for member in self.ENUMS[definition]]

    @pytest.mark.parametrize(
        "document", [SAMPLES.text_document(), SAMPLES.spreadsheet(), SAMPLES.failed()]
    )
    def test_encoded_documents_are_valid(self, document: ParsedDocument) -> None:
        self.VALIDATOR.validate(self.ENCODER.encode(document))

    def test_an_element_without_a_locator_is_rejected(self) -> None:
        encoded = self.ENCODER.encode(SAMPLES.text_document())
        elements = encoded[OutputField.ELEMENTS]
        assert isinstance(elements, list)
        first = elements[0]
        assert isinstance(first, dict)
        del first[OutputField.LOCATOR]

        assert not self.VALIDATOR.is_valid(encoded)

    def test_a_failed_result_without_a_reason_is_rejected(self) -> None:
        encoded = self.ENCODER.encode(SAMPLES.failed())
        del encoded[OutputField.FAILURE_REASON]

        assert not self.VALIDATOR.is_valid(encoded)
