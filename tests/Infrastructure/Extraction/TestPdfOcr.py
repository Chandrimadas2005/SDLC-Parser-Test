from pathlib import Path
from typing import ClassVar, Final

import pypdfium2
import pytest

from ParserService.Domain.Documents import DocumentStatus, ParsedDocument, SourceFile, WarningCode
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import (
    ExtractorRegistry,
    OcrText,
    ParsePipeline,
    PdfPageOcr,
    TesseractOcr,
)
from tests.Samples import SamplePdfs

NEEDS_OCR: Final = pytest.mark.skipif(
    TesseractOcr.available() is None, reason="Tesseract is not installed"
)


class _FaintPageOcr(PdfPageOcr):
    def recognise(self, page: pypdfium2.PdfPage) -> OcrText | None:
        del page
        return OcrText("Faint synthetic text", 0.3)


class _NoOcrPages(PdfPageOcr):
    MAX_PAGES: ClassVar[int] = 0


class TestPdfOcr:
    """Scanned PDF pages are read with OCR; pages with a text layer are left as they are."""

    @staticmethod
    def _parse(path: Path) -> Result[ParsedDocument, FailureReason]:
        pipeline = ParsePipeline(
            MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
            ExtractorRegistry.default(),
        )
        return pipeline.parse(SourceFile(str(path), FileName(path.name)))

    @NEEDS_OCR
    def test_scanned_page_is_read_and_flagged(self, tmp_path: Path) -> None:
        document = self._parse(SamplePdfs().scanned(tmp_path / "scan.pdf")).unwrap()

        pages = {element.locator.page: element.text or "" for element in document.elements}
        codes = [(w.code, w.locator.page if w.locator else None) for w in document.warnings]
        assert document.status is DocumentStatus.SUCCEEDED
        assert "Cover page" in pages[1]
        assert "1250" in pages[2]
        assert codes == [(WarningCode.OCR_APPLIED, 2)]
        assert float((document.facts.properties or {})["ocr_confidence"]) >= 0.6

    def test_low_confidence_page_is_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        faint = _FaintPageOcr(TesseractOcr("tesseract"))
        monkeypatch.setattr(PdfPageOcr, "available", classmethod(lambda _cls: faint))

        document = self._parse(SamplePdfs().scanned(tmp_path / "scan.pdf")).unwrap()

        codes = [w.code for w in document.warnings]
        assert codes == [WarningCode.OCR_APPLIED, WarningCode.OCR_LOW_CONFIDENCE]

    def test_pages_beyond_the_ocr_limit_stay_unreadable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        capped = _NoOcrPages(TesseractOcr("tesseract"))
        monkeypatch.setattr(PdfPageOcr, "available", classmethod(lambda _cls: capped))

        document = self._parse(SamplePdfs().scanned(tmp_path / "scan.pdf")).unwrap()

        assert document.status is DocumentStatus.PARTIAL
        assert [w.code for w in document.warnings] == [WarningCode.PAGE_UNREADABLE]
