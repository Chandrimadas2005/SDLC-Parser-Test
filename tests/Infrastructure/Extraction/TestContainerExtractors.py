import zipfile
from pathlib import Path

from ParserService.Domain.Documents import (
    DocumentStatus,
    ElementKind,
    ParsedDocument,
    SourceFile,
    WarningCode,
)
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Config import Limits
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import ExtractorRegistry, ParsePipeline
from tests.Samples import SampleContainers


class TestContainerExtractors:
    """ZIP archives and e-mails: every part is parsed and kept apart under its own heading."""

    PIPELINE = ParsePipeline(
        MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
        ExtractorRegistry.default(),
    )

    def _parse(self, path: Path) -> Result[ParsedDocument, FailureReason]:
        return self.PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

    @staticmethod
    def _headings(document: ParsedDocument) -> list[str]:
        return [
            e.text or ""
            for e in document.elements
            if e.kind is ElementKind.HEADING and e.level == 1
        ]

    def test_archive_entries_are_parsed_safely(self, tmp_path: Path) -> None:
        document = self._parse(SampleContainers().archive(tmp_path / "bundle.zip")).unwrap()

        titles = [entry.name for entry in document.outline]
        tables = [e for e in document.elements if e.kind is ElementKind.TABLE]
        assert titles == ["guide.md", "data/tasks.csv", "report.docx", "inner.zip", "../escape.txt"]
        assert document.status is DocumentStatus.SUCCEEDED
        assert len(tables) >= 2
        assert not (tmp_path.parent / "escape.txt").exists()

    def test_archives_nested_too_deep_are_skipped(self, tmp_path: Path) -> None:
        document = self._parse(SampleContainers().nested(tmp_path / "deep.zip", 6)).unwrap()

        assert document.status is DocumentStatus.PARTIAL
        assert WarningCode.ELEMENT_SKIPPED in [w.code for w in document.warnings]

    def test_archive_limits_are_checked_before_decompressing(self, tmp_path: Path) -> None:
        path = tmp_path / "many.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for n in range(Limits().archive_max_files + 1):
                archive.writestr(f"part-{n}.txt", "")

        assert self._parse(path).unwrap_err() is FailureReason.LIMIT_EXCEEDED

    def test_email_body_attachment_and_headers(self, tmp_path: Path) -> None:
        document = self._parse(SampleContainers().email(tmp_path / "update.eml")).unwrap()

        texts = " ".join(e.text or "" for e in document.elements)
        properties = document.facts.properties or {}
        assert self._headings(document) == ["Message body", "tasks.csv"]
        assert "pilot starts next week" in texts
        assert properties["email_subject"] == "Synthetic status update"
        assert any(e.kind is ElementKind.TABLE for e in document.elements)

    def test_html_only_email_body_becomes_text(self, tmp_path: Path) -> None:
        document = self._parse(
            SampleContainers().email(tmp_path / "h.eml", html_only=True)
        ).unwrap()

        texts = [e.text or "" for e in document.elements]
        assert "Hello from HTML." in texts
        assert "Second line." in texts

    def test_broken_containers_fail_cleanly(self, tmp_path: Path) -> None:
        archive = tmp_path / "broken.zip"
        archive.write_bytes(b"PK\x03\x04" + b"\x00" * 40)
        message = tmp_path / "broken.msg"
        message.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 600)

        assert self._parse(archive).is_err
        assert self._parse(message).is_err
