import zipfile
from pathlib import Path
from typing import Final

import pytest

from ParserService.Domain.Documents import DetectedType, SourceFile, WarningCode
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Detection import (
    FileExtension,
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)

CORPUS: Final = Path(__file__).resolve().parents[2] / "corpus"


class TestMagicTypeDetector:
    """The real type comes from the content; the extension is only a hint."""

    DETECTOR = MagicTypeDetector(TextEncodingDetector(), ZipContentInspector())

    def _detect_file(self, path: Path, name: str) -> tuple[DetectedType, list[WarningCode]]:
        detection = self.DETECTOR.detect(SourceFile(str(path), FileName(name))).unwrap()
        return detection.detected_type, [warning.code for warning in detection.warnings]

    @staticmethod
    def _zip(path: Path, entries: dict[str, bytes]) -> Path:
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
        return path

    @pytest.mark.parametrize(
        ("relative", "name", "expected"),
        [
            ("txt/normal/notes.txt", "notes.txt", DetectedType.TXT),
            ("md/normal/guide.md", "guide.md", DetectedType.MD),
            ("md/normal/guide.md", "guide.markdown", DetectedType.MD),
            ("txt/empty/empty.txt", "empty.txt", DetectedType.TXT),
        ],
    )
    def test_text_files_use_the_extension_inside_the_text_family(
        self, relative: str, name: str, expected: DetectedType
    ) -> None:
        assert self._detect_file(CORPUS / relative, name) == (expected, [])

    def test_wrong_extension_parses_by_content_and_warns(self) -> None:
        path = CORPUS / "txt/wrong-extension/notes.pdf"

        assert self._detect_file(path, "notes.pdf") == (
            DetectedType.TXT,
            [WarningCode.EXTENSION_MISMATCH],
        )

    def test_legacy_encoding_is_detected_and_flagged_as_guessed(self) -> None:
        detection = self.DETECTOR.detect(
            SourceFile(str(CORPUS / "txt/normal/latin1.txt"), FileName("latin1.txt"))
        ).unwrap()

        assert detection.encoding is not None
        assert detection.encoding not in {"ascii", "utf_8"}
        assert [warning.code for warning in detection.warnings] == [WarningCode.ENCODING_GUESSED]

    def test_pdf_header_wins_over_a_text_extension(self, tmp_path: Path) -> None:
        path = tmp_path / "report.txt"
        path.write_bytes(b"%PDF-1.4\n%synthetic\n")

        assert self._detect_file(path, "report.txt") == (
            DetectedType.PDF,
            [WarningCode.EXTENSION_MISMATCH],
        )

    @pytest.mark.parametrize(
        ("entries", "expected"),
        [
            ({"word/document.xml": b"<w/>"}, DetectedType.DOCX),
            ({"xl/workbook.xml": b"<x/>"}, DetectedType.XLSX),
            ({"xl/workbook.xml": b"<x/>", "xl/vbaProject.bin": b"0"}, DetectedType.XLSM),
            ({"ppt/presentation.xml": b"<p/>"}, DetectedType.PPTX),
            ({"mimetype": b"application/vnd.oasis.opendocument.text"}, DetectedType.ODT),
            ({"mimetype": b"application/vnd.oasis.opendocument.spreadsheet"}, DetectedType.ODS),
            ({"mimetype": b"application/epub+zip"}, DetectedType.ZIP),
            ({"notes.txt": b"hello"}, DetectedType.ZIP),
        ],
    )
    def test_zip_based_formats_are_told_apart_by_their_contents(
        self, tmp_path: Path, entries: dict[str, bytes], expected: DetectedType
    ) -> None:
        path = self._zip(tmp_path / "upload.bin", entries)

        assert self._detect_file(path, "upload")[0] is expected

    def test_legacy_office_uses_the_extension_inside_the_ole_family(self, tmp_path: Path) -> None:
        path = tmp_path / "old.doc"
        path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 600)

        assert self._detect_file(path, "old.doc") == (DetectedType.DOC, [])
        assert self.DETECTOR.detect(SourceFile(str(path), FileName("old.bin"))).is_err

    @pytest.mark.parametrize("content", [bytes(range(256)) * 4, b"PK\x03\x04 truncated archive"])
    def test_unknown_or_broken_binary_is_unsupported_never_guessed(
        self, tmp_path: Path, content: bytes
    ) -> None:
        path = tmp_path / "mystery.txt"
        path.write_bytes(content)

        result = self.DETECTOR.detect(SourceFile(str(path), FileName("mystery.txt")))

        assert result.unwrap_err() is FailureReason.UNSUPPORTED_TYPE

    def test_source_location_must_not_be_blank(self) -> None:
        with pytest.raises(ValueError, match="blank"):
            SourceFile(" ", FileName("a.txt"))

    def test_every_known_extension_hints_a_detected_type(self) -> None:
        hinted = {extension.hinted_type for extension in FileExtension}

        assert DetectedType.JPEG in hinted
        assert FileExtension.of(FileName("SCAN.TIF")) is FileExtension.TIF
        assert FileExtension.of(FileName("archive.tar")) is None
