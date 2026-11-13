import tempfile
from pathlib import Path
from typing import ClassVar, Final, Self

import pypdfium2

from ParserService.Infrastructure.Extraction.OcrText import OcrText
from ParserService.Infrastructure.Extraction.TesseractOcr import TesseractOcr


class PdfPageOcr:
    """Reads a PDF page that has no text layer (a scan) with Tesseract.

    The page is rendered to grayscale pixels by PDFium and written as a PGM image,
    which Tesseract reads directly, so no imaging library is needed. At most
    ``MAX_PAGES`` pages of one file are OCR'd, so a long scan stays inside the job's
    time limit; the rest are reported as unreadable.
    """

    DPI: Final = 300
    POINTS_PER_INCH: Final = 72
    MAX_PAGES: ClassVar[int] = 50

    def __init__(self, ocr: TesseractOcr) -> None:
        self._ocr = ocr

    @classmethod
    def available(cls) -> Self | None:
        """OCR for PDF pages, or ``None`` when Tesseract is not installed."""
        ocr = TesseractOcr.available()
        return None if ocr is None else cls(ocr)

    def recognise(self, page: pypdfium2.PdfPage) -> OcrText | None:
        """Recognise the text of one page.

        Args:
            page: An open PDFium page.

        Returns:
            The text and its confidence, or ``None`` when OCR failed.
        """
        with tempfile.TemporaryDirectory(prefix="ocr-") as folder:
            image = Path(folder) / "page.pgm"
            self._render(page, image)
            result = self._ocr.read(image)
        return result.unwrap() if result.is_ok else None

    def _render(self, page: pypdfium2.PdfPage, image: Path) -> None:
        bitmap = page.render(scale=self.DPI / self.POINTS_PER_INCH, grayscale=True)
        width, height, stride = bitmap.width, bitmap.height, bitmap.stride
        pixels = bytes(bitmap.buffer)
        rows = (pixels[row * stride : row * stride + width] for row in range(height))
        image.write_bytes(f"P5\n{width} {height}\n255\n".encode() + b"".join(rows))
