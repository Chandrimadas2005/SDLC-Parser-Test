import zipfile
from pathlib import Path
from typing import Final

import pytest

from ParserService.Domain.Documents import DocumentStatus, ParseWarning, WarningCode
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason
from ParserService.Infrastructure.Config import Limits
from ParserService.Infrastructure.Extraction import SpreadsheetTableBuilder, ZipArchiveGuard
from ParserService.Infrastructure.Extraction.Ods import (
    OdsAttributes,
    OdsCellReader,
    OdsContentReader,
    OdsExtractor,
    OdsPropertyReader,
    OdsRowReader,
    OdsWorkbookReader,
)
from tests.Fakes import FakeExtractor
from tests.Infrastructure.Extraction.Ods.OdsHarness import OdsHarness
from tests.Samples import DocumentSamples

HARNESS: Final = OdsHarness()
P: Final = OdsHarness.PACKAGE


class TestOdsPackageFailures:
    """Broken, encrypted, oversized or empty packages get a precise reason (brief, 2.5)."""

    @staticmethod
    def _with_fallback(fallback: FakeExtractor) -> OdsExtractor:
        attributes = OdsAttributes()
        rows = OdsRowReader(OdsCellReader(attributes), attributes)
        reader = OdsWorkbookReader(
            ZipArchiveGuard(Limits()), OdsContentReader(rows, attributes), OdsPropertyReader()
        )
        return OdsExtractor(reader, SpreadsheetTableBuilder(), fallback)

    @pytest.mark.parametrize(
        "content", [b"not a zip at all", b"PK\x03\x04broken"], ids=["text", "zip-header"]
    )
    def test_a_file_that_is_not_a_package_is_corrupted(
        self, tmp_path: Path, content: bytes
    ) -> None:
        path = tmp_path / "broken.ods"
        path.write_bytes(content)

        assert HARNESS.extract(path).unwrap_err() is FailureReason.CORRUPTED_FILE

    def test_a_truncated_package_is_corrupted(self) -> None:
        path = OdsHarness.CORPUS / "corrupted" / "truncated.ods"

        assert HARNESS.extract(path).unwrap_err() is FailureReason.CORRUPTED_FILE

    @pytest.mark.parametrize(
        "content",
        [P.content([]), b"<office:document-content", b"<?xml version='1.0'?><x/>"],
        ids=["no-sheets", "broken-xml", "not-ods-xml"],
    )
    def test_a_package_without_readable_sheets_is_corrupted(
        self, tmp_path: Path, content: bytes
    ) -> None:
        path = P.write(tmp_path / "book.ods", content)

        assert HARNESS.extract(path).unwrap_err() is FailureReason.CORRUPTED_FILE

    def test_a_package_without_content_is_corrupted(self, tmp_path: Path) -> None:
        path = tmp_path / "book.ods"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("mimetype", P.MIMETYPE)

        assert HARNESS.extract(path).unwrap_err() is FailureReason.CORRUPTED_FILE

    def test_an_encrypted_package_is_password_protected(self, tmp_path: Path) -> None:
        extra = {"META-INF/manifest.xml": P.ENCRYPTED_MANIFEST}
        path = P.write(tmp_path / "secret.ods", b"\x00encrypted", extra)

        assert HARNESS.extract(path).unwrap_err() is FailureReason.PASSWORD_PROTECTED

    @pytest.mark.parametrize(
        "limits", [Limits(archive_max_expanded_bytes=10), Limits(archive_max_files=1)]
    )
    def test_archive_limits_are_checked_first(self, limits: Limits) -> None:
        path = OdsHarness.CORPUS / "normal" / "normal.ods"

        result = HARNESS.extract(path, OdsHarness.extractor(limits))

        assert result.unwrap_err() is FailureReason.LIMIT_EXCEEDED

    def test_a_corrupted_package_is_repaired_by_the_fallback(self) -> None:
        repaired = DocumentSamples().spreadsheet()
        extractor = self._with_fallback(FakeExtractor(Result.ok(repaired)))
        path = OdsHarness.CORPUS / "corrupted" / "truncated.ods"

        document = HARNESS.extract(path, extractor).unwrap()

        assert document.status is DocumentStatus.PARTIAL
        assert document.warnings[-1] == ParseWarning(WarningCode.FILE_REPAIRED)

    def test_a_failed_repair_is_still_corrupted(self) -> None:
        failing = FakeExtractor(Result.err(FailureReason.TIMEOUT))
        path = OdsHarness.CORPUS / "corrupted" / "truncated.ods"

        result = HARNESS.extract(path, self._with_fallback(failing))

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE

    def test_other_failures_are_never_sent_to_the_fallback(self, tmp_path: Path) -> None:
        extra = {"META-INF/manifest.xml": P.ENCRYPTED_MANIFEST}
        path = P.write(tmp_path / "secret.ods", b"x", extra)
        extractor = self._with_fallback(FakeExtractor(Result.ok(DocumentSamples().spreadsheet())))

        assert HARNESS.extract(path, extractor).unwrap_err() is FailureReason.PASSWORD_PROTECTED

    def test_a_missing_meta_file_gives_no_properties(self, tmp_path: Path) -> None:
        sheet = P.sheet("Only", [P.row([P.text("x")])])
        path = P.write(tmp_path / "book.ods", P.content([sheet]), {"meta.xml": b"<broken"})

        document = HARNESS.extract(path).unwrap()

        assert (
            document.facts.properties
            == DocumentSamples().facts(document.facts.detected_type).properties
        )
