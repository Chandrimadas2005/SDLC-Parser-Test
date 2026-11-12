from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OcrText:
    """Text recognised by OCR, with paragraphs separated by blank lines, and its confidence."""

    text: str
    confidence: float
