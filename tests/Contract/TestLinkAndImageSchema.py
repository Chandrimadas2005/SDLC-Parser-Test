import json
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ParserService.Domain.Documents import (
    DetectedType,
    DocumentStatus,
    Element,
    ElementId,
    ElementKind,
    ImageSource,
    Locator,
    Metrics,
    ParsedDocument,
)
from ParserService.Infrastructure.Output import OutputField, ParsedDocumentJsonEncoder
from tests.Samples import DocumentSamples

SCHEMA_PATH: Final = Path(__file__).resolve().parents[2] / "schemas" / "parsed_document.v1.json"


class TestLinkAndImageSchema:
    """Schema 1.2: links carry an href, images a source and size, and nothing else does."""

    VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    ENCODER = ParsedDocumentJsonEncoder()
    LOCATOR = Locator.for_text(1, 0, 4)

    def _document(self) -> ParsedDocument:
        elements = (
            Element(ElementId.at(1), ElementKind.LINK, self.LOCATOR, "Docs", href="/docs"),
            Element(
                ElementId.at(2),
                ElementKind.IMAGE,
                self.LOCATOR,
                "Chart",
                image=ImageSource("chart.png", 640, 480),
            ),
        )
        return ParsedDocument(
            DocumentStatus.SUCCEEDED,
            DocumentSamples().facts(DetectedType.HTML),
            elements,
            (),
            (),
            Metrics.for_elements(elements, {}),
        )

    def test_links_and_images_encode_their_new_fields(self) -> None:
        encoded = json.loads(self.ENCODER.to_json(self._document()))
        link, image = encoded[OutputField.ELEMENTS]

        assert link[OutputField.HREF] == "/docs"
        assert {key: image[key] for key in ("source", "width", "height")} == {
            "source": "chart.png",
            "width": 640,
            "height": 480,
        }
        self.VALIDATOR.validate(encoded)

    def test_an_image_without_size_leaves_the_fields_out(self) -> None:
        element = Element(
            ElementId.at(1), ElementKind.IMAGE, self.LOCATOR, image=ImageSource("a.png")
        )

        document = self._document()
        only = replace(document, elements=(element,), metrics=Metrics.for_elements((element,), {}))

        encoded = json.loads(self.ENCODER.to_json(only))[OutputField.ELEMENTS][0]

        assert encoded[OutputField.SOURCE] == "a.png"
        assert OutputField.WIDTH not in encoded

    @pytest.mark.parametrize(
        ("kind", "field", "value"),
        [("paragraph", "href", "/x"), ("link", "source", "a.png"), ("paragraph", "width", 3)],
    )
    def test_the_schema_rejects_fields_on_the_wrong_kind(
        self, kind: str, field: str, value: object
    ) -> None:
        encoded = json.loads(self.ENCODER.to_json(DocumentSamples().text_document()))
        element = encoded[OutputField.ELEMENTS][1]
        element[OutputField.KIND] = kind
        element[field] = value

        with pytest.raises(ValidationError):
            self.VALIDATOR.validate(encoded)
