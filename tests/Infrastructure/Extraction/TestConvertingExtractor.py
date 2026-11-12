import shutil
from pathlib import Path
from typing import ClassVar, Final

import pytest

from ParserService.Domain.Documents import DetectedType, ElementKind, ParsedDocument, SourceFile
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import (
    ExtractorRegistry,
    LibreOfficeConverter,
    ParsePipeline,
)

OFFICE: Final = LibreOfficeConverter.available()
NEEDS_OFFICE: Final = pytest.mark.skipif(OFFICE is None, reason="LibreOffice is not installed")
RTF: Final = b"{\\rtf1\\ansi{\\b Synthetic heading}\\par Synthetic rich text paragraph.\\par}"


class _SlowConverter(LibreOfficeConverter):
    TIMEOUT_SECONDS: ClassVar[float] = 0.001


class TestConvertingExtractor:
    """Legacy formats are converted by LibreOffice, then parsed by the modern extractors."""

    PIPELINE = ParsePipeline(
        MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
        ExtractorRegistry.default(),
    )

    def _parse(self, path: Path) -> Result[ParsedDocument, FailureReason]:
        return self.PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

    @NEEDS_OFFICE
    def test_rtf_is_converted_and_keeps_its_own_facts(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.rtf"
        path.write_bytes(RTF)

        document = self._parse(path).unwrap()

        assert document.facts.detected_type is DetectedType.RTF
        assert document.facts.size_bytes == len(RTF)
        assert [element.text for element in document.elements] == [
            "Synthetic heading",
            "Synthetic rich text paragraph.",
        ]

    @NEEDS_OFFICE
    def test_odt_goes_through_the_docx_extractor(self, tmp_path: Path) -> None:
        assert OFFICE is not None
        rtf = tmp_path / "notes.rtf"
        rtf.write_bytes(RTF)
        odt = OFFICE.convert(rtf, DetectedType.ODT, tmp_path / "odt").unwrap()

        document = self._parse(odt).unwrap()

        texts = [e.text for e in document.elements if e.kind is ElementKind.PARAGRAPH]
        assert document.facts.detected_type is DetectedType.ODT
        assert "Synthetic rich text paragraph." in texts

    @NEEDS_OFFICE
    def test_unconvertible_file_fails_as_corrupted(self, tmp_path: Path) -> None:
        assert OFFICE is not None
        path = tmp_path / "broken.doc"
        path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 600)

        result = OFFICE.convert(path, DetectedType.DOCX, tmp_path / "out")

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE

    @NEEDS_OFFICE
    def test_slow_conversion_is_stopped(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.rtf"
        path.write_bytes(RTF)
        executable = shutil.which(LibreOfficeConverter.EXECUTABLE)
        assert executable is not None

        result = _SlowConverter(executable).convert(path, DetectedType.DOCX, tmp_path / "out")

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE

    def test_without_libreoffice_legacy_formats_are_not_registered(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(shutil, "which", lambda _name: None)

        supported = ExtractorRegistry.default().supported_types

        assert LibreOfficeConverter.available() is None
        assert DetectedType.RTF not in supported
        assert DetectedType.DOCX in supported
