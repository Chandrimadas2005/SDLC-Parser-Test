from pathlib import Path
from typing import Final

import pytest

from ParserService.Domain.Documents import (
    DetectedType,
    Detection,
    DocumentFacts,
    ElementKind,
    ExtractionRequest,
    ParsedDocument,
    SourceFile,
    WarningCode,
)
from ParserService.Domain.Jobs import FailureReason, FileHash, FileName
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import (
    ExtractorRegistry,
    LibreOfficeConverter,
    ParsePipeline,
    TesseractOcr,
)
from ParserService.Infrastructure.Output import ParsedDocumentJsonEncoder

TESTS: Final = Path(__file__).resolve().parents[2]
CORPUS: Final = TESTS / "corpus"
GOLDEN: Final = TESTS / "golden" / "extraction"


class TestParsePipeline:
    """Text and Markdown files parse end to end, matching their golden files."""

    PIPELINE = ParsePipeline(
        MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
        ExtractorRegistry.default(),
    )
    ENCODER = ParsedDocumentJsonEncoder()

    def _parse(self, path: Path, name: str) -> ParsedDocument:
        return self.PIPELINE.parse(SourceFile(str(path), FileName(name))).unwrap()

    @pytest.mark.parametrize(
        ("relative", "golden"),
        [
            ("txt/normal/notes.txt", "txt_notes.json"),
            ("md/normal/guide.md", "md_guide.json"),
            ("txt/empty/empty.txt", "txt_empty.json"),
            ("txt/wrong-extension/notes.pdf", "txt_wrong_extension.json"),
        ],
    )
    def test_corpus_file_matches_its_golden_file(self, relative: str, golden: str) -> None:
        path = CORPUS / relative

        document = self._parse(path, path.name)

        assert self.ENCODER.to_json(document) == (GOLDEN / golden).read_text(encoding="utf-8")

    def test_every_locator_points_at_its_text(self) -> None:
        path = CORPUS / "md/normal/guide.md"
        text = path.read_text(encoding="utf-8")

        for element in self._parse(path, "guide.md").elements:
            start, end = element.locator.char_start, element.locator.char_end
            assert start is not None
            assert end is not None
            assert element.text is not None
            assert element.text.split()[0] in text[start:end]

    def test_legacy_encoding_is_decoded_and_flagged(self) -> None:
        document = self._parse(CORPUS / "txt/normal/latin1.txt", "latin1.txt")

        assert document.elements[0].text is not None
        assert document.elements[0].text.startswith("Le café est prêt.")
        assert [warning.code for warning in document.warnings] == [WarningCode.ENCODING_GUESSED]

    def test_windows_line_endings_keep_offsets_exact(self, tmp_path: Path) -> None:
        path = tmp_path / "crlf.txt"
        path.write_bytes(b"First line\r\nsame paragraph\r\n\r\nSecond\r\n")
        text = path.read_bytes().decode()

        elements = self._parse(path, "crlf.txt").elements

        assert [element.text for element in elements] == ["First line\r\nsame paragraph", "Second"]
        second = elements[1].locator
        assert text[second.char_start : second.char_end] == "Second"

    def test_markdown_edge_cases(self, tmp_path: Path) -> None:
        path = tmp_path / "edge.md"
        path.write_text("#\n## Title ##\nsoft\nwrap\n```\nnever closed\n", encoding="utf-8")

        elements = self._parse(path, "edge.md").elements

        assert [(element.kind, element.text) for element in elements] == [
            (ElementKind.PARAGRAPH, "#"),
            (ElementKind.HEADING, "Title"),
            (ElementKind.PARAGRAPH, "soft wrap"),
            (ElementKind.PARAGRAPH, "never closed"),
        ]

    def test_unsupported_content_and_formats_without_an_extractor_fail(
        self, tmp_path: Path
    ) -> None:
        binary = tmp_path / "blob.txt"
        binary.write_bytes(bytes(range(256)) * 4)
        image = tmp_path / "scan.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)

        for path in (binary, image):
            result = self.PIPELINE.parse(SourceFile(str(path), FileName(path.name)))
            assert result.unwrap_err() is FailureReason.UNSUPPORTED_TYPE

    NATIVE: Final = (
        DetectedType.XLSX,
        DetectedType.XLSM,
        DetectedType.XLS,
        DetectedType.CSV,
        DetectedType.TSV,
        DetectedType.PDF,
        DetectedType.DOCX,
        DetectedType.TXT,
        DetectedType.MD,
        DetectedType.PPTX,
        DetectedType.HTML,
        DetectedType.ODS,
        DetectedType.EML,
        DetectedType.MSG,
        DetectedType.ZIP,
    )
    CONVERTED: Final = (
        DetectedType.ODT,
        DetectedType.RTF,
        DetectedType.DOC,
        DetectedType.PPT,
    )

    IMAGES: Final = (DetectedType.PNG, DetectedType.JPEG, DetectedType.TIFF)

    def test_registry_lists_supported_types_in_priority_order(self) -> None:
        office = self.CONVERTED if LibreOfficeConverter.available() else ()
        images = self.IMAGES if TesseractOcr.available() else ()
        expected = tuple(kind for kind in DetectedType if kind in self.NATIVE + office + images)

        assert ExtractorRegistry.default().supported_types == expected

    def test_request_rejects_facts_that_disagree_with_detection(self) -> None:
        facts = DocumentFacts(FileName("a.txt"), DetectedType.TXT, 1, FileHash.of(b"a"))
        detection = Detection(DetectedType.MD, "utf_8", ())

        with pytest.raises(ValueError, match="agree"):
            ExtractionRequest(SourceFile("a.txt", FileName("a.txt")), facts, detection)
