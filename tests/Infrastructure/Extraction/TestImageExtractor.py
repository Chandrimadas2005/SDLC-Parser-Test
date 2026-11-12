from pathlib import Path
from typing import Final

import pytest

from ParserService.Domain.Documents import (
    DetectedType,
    DocumentStatus,
    ParsedDocument,
    SourceFile,
    WarningCode,
)
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
    TesseractOcr,
)
from tests.Samples import SampleImages

NEEDS_OCR: Final = pytest.mark.skipif(
    TesseractOcr.available() is None, reason="Tesseract is not installed"
)


class _FaintOcr(TesseractOcr):
    def read(self, image: Path) -> Result[OcrText, FailureReason]:
        del image
        return Result.ok(OcrText("Faint synthetic text", 0.3))


class TestImageExtractor:
    """Images are read with OCR; the result says so and carries the confidence."""

    @staticmethod
    def _parse(path: Path) -> Result[ParsedDocument, FailureReason]:
        pipeline = ParsePipeline(
            MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
            ExtractorRegistry.default(),
        )
        return pipeline.parse(SourceFile(str(path), FileName(path.name)))

    @NEEDS_OCR
    def test_printed_text_is_recognised_with_its_confidence(self, tmp_path: Path) -> None:
        lines = ("Synthetic scanned invoice", "Total amount 1250")
        image = SampleImages().text(tmp_path / "invoice.png", lines)

        document = self._parse(image).unwrap()

        text = " ".join(element.text or "" for element in document.elements)
        properties = document.facts.properties or {}
        assert document.facts.detected_type is DetectedType.PNG
        assert "invoice" in text
        assert "1250" in text
        assert [w.code for w in document.warnings] == [WarningCode.OCR_APPLIED]
        assert float(properties["ocr_confidence"]) >= 0.6

    @NEEDS_OCR
    def test_image_without_text_is_partial(self, tmp_path: Path) -> None:
        document = self._parse(SampleImages().blank(tmp_path / "blank.png")).unwrap()

        assert document.status is DocumentStatus.PARTIAL
        assert WarningCode.PAGE_UNREADABLE in [w.code for w in document.warnings]

    def test_low_confidence_is_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        faint = _FaintOcr("tesseract")
        monkeypatch.setattr(TesseractOcr, "available", classmethod(lambda _cls: faint))
        image = SampleImages().text(tmp_path / "faint.png", ("Faint",))

        document = self._parse(image).unwrap()

        codes = [w.code for w in document.warnings]
        assert codes == [WarningCode.OCR_APPLIED, WarningCode.OCR_LOW_CONFIDENCE]
        assert (document.facts.properties or {})["ocr_confidence"] == "0.30"
