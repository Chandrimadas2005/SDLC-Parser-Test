import json
from pathlib import Path
from typing import Final

import pytest

from ParserService.Domain.Documents.Element import Element
from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Config.Limits import Limits
from ParserService.Infrastructure.Detection.MagicTypeDetector import MagicTypeDetector
from ParserService.Infrastructure.Detection.TextEncodingDetector import TextEncodingDetector
from ParserService.Infrastructure.Detection.ZipContentInspector import ZipContentInspector
from ParserService.Infrastructure.Extraction.ExtractorRegistry import ExtractorRegistry
from ParserService.Infrastructure.Extraction.ParsePipeline import ParsePipeline
from ParserService.Infrastructure.Output.ParsedDocumentJsonEncoder import ParsedDocumentJsonEncoder

TESTS: Final = Path(__file__).resolve().parents[2]
CORPUS: Final = TESTS / "corpus"
GOLDEN: Final = TESTS / "golden" / "extraction"
ENCODER: Final = ParsedDocumentJsonEncoder()
PIPELINE_DETECTOR: Final = MagicTypeDetector(TextEncodingDetector(), ZipContentInspector())
PIPELINE: Final = ParsePipeline(PIPELINE_DETECTOR, ExtractorRegistry.default())


class TestStructuredDataExtractors:
    """End-to-end tests for JSON, YAML and safe XML extraction."""

    @pytest.mark.parametrize(
        ("format_name", "extension"),
        [("json", "json"), ("yaml", "yaml"), ("xml", "xml")],
    )
    def test_normal_corpus_matches_golden(self, format_name: str, extension: str) -> None:
        path = CORPUS / format_name / "normal" / f"records.{extension}"
        golden = (GOLDEN / f"{format_name}_records.json").read_text(encoding="utf-8")
        document = PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()

        assert ENCODER.to_json(document) == golden
        self._assert_source_locators(path, document.elements)

    @pytest.mark.parametrize(
        ("format_name", "extension"),
        [("json", "json"), ("yaml", "yaml"), ("xml", "xml")],
    )
    def test_empty_corpus_has_a_defined_result(self, format_name: str, extension: str) -> None:
        path = CORPUS / format_name / "empty" / f"empty.{extension}"
        document = PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()

        assert document.facts.detected_type.value == format_name
        assert document.status.value == "succeeded"
        assert document.elements == ()

    @pytest.mark.parametrize(
        ("format_name", "extension"),
        [("json", "json"), ("yaml", "yaml"), ("xml", "xml")],
    )
    def test_invalid_syntax_returns_corrupted_file(self, format_name: str, extension: str) -> None:
        path = CORPUS / format_name / "invalid" / f"invalid.{extension}"

        result = PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE

    @pytest.mark.parametrize(
        ("format_name", "extension"),
        [("json", "json"), ("yaml", "yaml"), ("xml", "xml")],
    )
    def test_deep_nesting_returns_limit_exceeded(self, format_name: str, extension: str) -> None:
        path = CORPUS / format_name / "deeply-nested" / f"deep.{extension}"

        result = PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

        assert result.unwrap_err() is FailureReason.LIMIT_EXCEEDED

    @pytest.mark.parametrize("format_name", ["json", "yaml", "xml"])
    def test_content_detection_wins_over_wrong_extension(self, format_name: str) -> None:
        path = CORPUS / format_name / "wrong-extension" / "records.txt"

        document = PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()

        assert document.facts.detected_type.value == format_name
        assert any(warning.code.value == "extension_mismatch" for warning in document.warnings)

    def test_xml_attributes_and_mixed_text_are_kept(self, tmp_path: Path) -> None:
        path = tmp_path / "attributes.xml"
        path.write_text(
            '<root><item id="REQ-1">Login</item><note>before<b>bold</b>after</note></root>',
            encoding="utf-8",
        )

        document = PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()
        texts = {element.text for element in document.elements}

        assert "item.@id: REQ-1" in texts
        assert "item.#text: Login" in texts
        assert "note.#text: before after" in texts

    @pytest.mark.parametrize(
        ("extension", "payload"),
        [("json", '{"a": {"b": {"c": 1}}}'), ("yaml", "a:\n  b:\n    c: 1\n")],
    )
    def test_configured_depth_limit_is_applied(
        self, tmp_path: Path, extension: str, payload: str
    ) -> None:
        path = tmp_path / f"nested.{extension}"
        path.write_text(payload, encoding="utf-8")
        registry = ExtractorRegistry.default(None, Limits(structured_max_depth=3))
        pipeline = ParsePipeline(PIPELINE_DETECTOR, registry)

        result = pipeline.parse(SourceFile(str(path), FileName(path.name)))

        assert result.unwrap_err() is FailureReason.LIMIT_EXCEEDED

    def test_repeated_values_point_at_their_own_occurrence(self, tmp_path: Path) -> None:
        path = tmp_path / "repeated.json"
        source = '{"first": {"count": 2}, "second": {"count": 2}}'
        path.write_text(source, encoding="utf-8")

        document = PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()
        starts = [
            e.locator.char_start for e in document.elements if e.kind is ElementKind.PARAGRAPH
        ]

        assert starts == [source.index("2"), source.rindex("2")]

    def test_text_that_only_looks_like_xml_stays_text(self, tmp_path: Path) -> None:
        path = tmp_path / "note.txt"
        path.write_text("<b>bold</i> is not xml >", encoding="utf-8")

        document = PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()

        assert document.facts.detected_type.value == "txt"

    def test_five_thousand_records_are_not_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "records.json"
        rows = [{"id": index, "name": f"n{index}"} for index in range(5_000)]
        path.write_text(json.dumps({"records": rows}), encoding="utf-8")

        document = PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()

        assert document.elements[1].kind is ElementKind.TABLE

    @pytest.mark.parametrize(
        ("extension", "payload"),
        [("json", '[{"id": 1, "name": "Ada"}]'), ("yaml", "- id: 1\n  name: Ada\n")],
    )
    def test_root_array_of_objects_becomes_a_table(
        self, tmp_path: Path, extension: str, payload: str
    ) -> None:
        path = tmp_path / f"root.{extension}"
        path.write_text(payload, encoding="utf-8")

        document = PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()

        assert document.elements[0].text == "root"
        assert document.elements[1].kind is ElementKind.TABLE

    def test_non_standard_json_constant_is_corrupted(self, tmp_path: Path) -> None:
        path = tmp_path / "nonstandard.json"
        path.write_text('{"value": NaN}', encoding="utf-8")

        result = PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE

    def test_recursive_yaml_alias_is_limited(self, tmp_path: Path) -> None:
        path = tmp_path / "recursive.yaml"
        path.write_text("value: &value [*value]", encoding="utf-8")

        result = PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

        assert result.unwrap_err() is FailureReason.LIMIT_EXCEEDED

    @pytest.mark.parametrize(
        ("format_name", "extension"),
        [("json", "json"), ("yaml", "yaml"), ("xml", "xml")],
    )
    def test_element_count_limit_returns_limit_exceeded(
        self, tmp_path: Path, format_name: str, extension: str
    ) -> None:
        path = tmp_path / f"many.{extension}"
        path.write_text(self._large_payload(format_name), encoding="utf-8")

        result = PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

        assert result.unwrap_err() is FailureReason.LIMIT_EXCEEDED

    @staticmethod
    def _large_payload(format_name: str) -> str:
        if format_name == "json":
            return json.dumps({f"key{index}": index for index in range(100_001)})
        if format_name == "yaml":
            return "\n".join(f"key{index}: {index}" for index in range(100_001))
        children = "".join(f"<item>{index}</item>" for index in range(100_001))
        return f"<root>{children}</root>"

    @pytest.mark.parametrize(
        "payload",
        [
            '<!DOCTYPE root [<!ENTITY x SYSTEM "file:///etc/passwd">]><root>&x;</root>',
            '<!DOCTYPE r [<!ENTITY a "a"><!ENTITY b "&a;&a;&a;">]><r>&b;</r>',
        ],
    )
    def test_xml_entity_attacks_return_limit_exceeded(self, tmp_path: Path, payload: str) -> None:
        path = tmp_path / "hostile.xml"
        path.write_text(payload, encoding="utf-8")

        result = PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

        assert result.unwrap_err() is FailureReason.LIMIT_EXCEEDED

    @staticmethod
    def _assert_source_locators(path: Path, elements: tuple[Element, ...]) -> None:
        source = path.read_text(encoding="utf-8")
        for item in elements:
            locator = item.locator
            assert locator.paragraph is not None
            assert locator.char_start is not None
            assert locator.char_end is not None
            assert 0 <= locator.char_start <= locator.char_end <= len(source)
            if item.kind is ElementKind.PARAGRAPH and item.text is not None:
                value = item.text.split(": ", maxsplit=1)[1]
                assert source[locator.char_start : locator.char_end] == value
