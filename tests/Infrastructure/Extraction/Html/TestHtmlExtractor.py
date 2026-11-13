from pathlib import Path

import pytest

from ParserService.Domain.Documents import (
    DetectedType,
    Detection,
    ExtractionRequest,
    ParsedDocument,
    SourceFile,
)
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Domain.Ports import Extractor
from ParserService.Infrastructure.Extraction import ExtractorRegistry
from tests.Samples import DocumentSamples


class TestHtmlExtractor:
    """HTML files are read from disk, decoded and parsed without running anything."""

    EXTRACTOR: Extractor = ExtractorRegistry.default().for_type(DetectedType.HTML).unwrap()

    def _extract(self, path: Path) -> ParsedDocument:
        return self.EXTRACTOR.extract(self._request(path)).unwrap()

    @staticmethod
    def _request(path: Path) -> ExtractionRequest:
        detection = Detection(DetectedType.HTML, None, ())
        facts = DocumentSamples().facts(DetectedType.HTML)
        return ExtractionRequest(SourceFile(str(path), FileName(path.name)), facts, detection)

    def _texts(self, path: Path) -> list[str | None]:
        return [element.text for element in self._extract(path).elements]

    def test_a_declared_legacy_encoding_is_honoured(self, tmp_path: Path) -> None:
        path = tmp_path / "legacy.html"
        path.write_bytes(b'<meta charset="windows-1252"><p>caf\xe9 \x80</p>')

        assert self._texts(path) == ["café €"]

    def test_undeclared_utf8_is_detected(self, tmp_path: Path) -> None:
        path = tmp_path / "plain.html"
        text = f"naïve résumé {chr(0x2013)} ok"
        path.write_bytes(f"<p>{text}</p>".encode())

        assert self._texts(path) == [text]

    @pytest.mark.parametrize(
        "content",
        [b"index.html", b'<?xml version="1.0"?><html><body><p>x</p></body></html>'],
    )
    def test_markup_that_looks_like_a_path_or_xml_parses_without_warnings(
        self, tmp_path: Path, content: bytes
    ) -> None:
        path = tmp_path / "odd.html"
        path.write_bytes(content)

        assert self._extract(path).elements != ()

    def test_an_unreadable_file_is_corrupted(self, tmp_path: Path) -> None:
        result = self.EXTRACTOR.extract(self._request(tmp_path / "missing.html"))

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE
