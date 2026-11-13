from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PdfPageText:
    """The text of one PDF page, or ``None`` when the page could not be read.

    ``ocr_confidence`` is set when the text came from OCR instead of the text layer.
    """

    number: int
    text: str | None
    ocr_confidence: float | None = None
