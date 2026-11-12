from pathlib import Path
from typing import Final

import pypdfium2

from ParserService.Domain.Documents import DocumentStatus, ParsedDocument, SourceFile, WarningCode
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import ExtractorRegistry, ParsePipeline
from ParserService.Infrastructure.Output import ParsedDocumentJsonEncoder
from tests.Samples import SamplePdfs

GOLDEN: Final = Path(__file__).resolve().parents[2] / "golden" / "extraction"


class TestPdfExtractor:
    """PDFs give text per page with page locators, and fail precisely when they cannot."""

    PIPELINE = ParsePipeline(
        MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
        ExtractorRegistry.default(),
    )
    SAMPLES = SamplePdfs()

    def _parse(self, path: Path) -> Result[ParsedDocument, FailureReason]:
        return self.PIPELINE.parse(SourceFile(str(path), FileName(path.name)))

    def test_normal_pdf_matches_its_golden_file(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "normal.pdf")).unwrap()

        expected = (GOLDEN / "pdf_normal.json").read_text(encoding="utf-8")
        assert ParsedDocumentJsonEncoder().to_json(document) == expected

    def test_page_without_text_makes_the_result_partial(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "normal.pdf")).unwrap()

        assert document.status is DocumentStatus.PARTIAL
        assert document.facts.page_count == 3
        warning = document.warnings[0]
        assert warning.code is WarningCode.PAGE_UNREADABLE
        assert warning.locator is not None
        assert warning.locator.page == 3

    def test_locators_point_at_the_text_of_their_page(self, tmp_path: Path) -> None:
        path = self.SAMPLES.normal(tmp_path / "normal.pdf")
        document = self._parse(path).unwrap()
        pdf = pypdfium2.PdfDocument(path)

        for element in document.elements:
            locator = element.locator
            assert locator.page is not None
            page_text = str(pdf[locator.page - 1].get_textpage().get_text_range())
            assert (
                page_text[locator.char_start : locator.char_end].replace("\r\n", "\n")
                == element.text
            )
        pdf.close()

    def test_bookmarks_become_the_outline(self, tmp_path: Path) -> None:
        document = self._parse(self.SAMPLES.normal(tmp_path / "normal.pdf")).unwrap()

        outline = [(entry.name, entry.level, entry.locator.page) for entry in document.outline]
        assert outline == [("Introduction", 1, 1), ("Details", 2, 2)]

    def test_encrypted_pdf_fails_as_password_protected(self, tmp_path: Path) -> None:
        result = self._parse(self.SAMPLES.encrypted(tmp_path / "locked.pdf"))

        assert result.unwrap_err() is FailureReason.PASSWORD_PROTECTED

    def test_pdf_above_the_page_limit_is_rejected_before_reading(self, tmp_path: Path) -> None:
        path = self.SAMPLES.normal(tmp_path / "normal.pdf")
        limited = ParsePipeline(
            MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
            ExtractorRegistry.default(max_pages=2),
        )

        over = limited.parse(SourceFile(str(path), FileName(path.name)))
        within = ParsePipeline(
            MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
            ExtractorRegistry.default(max_pages=3),
        ).parse(SourceFile(str(path), FileName(path.name)))

        assert over.unwrap_err() is FailureReason.FILE_TOO_LARGE
        assert within.is_ok

    def test_truncated_pdf_fails_as_corrupted(self, tmp_path: Path) -> None:
        result = self._parse(self.SAMPLES.corrupted(tmp_path / "broken.pdf"))

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE
