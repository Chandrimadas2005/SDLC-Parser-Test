from typing import Final


class OcrConfidence:
    """Shared OCR settings: when confidence counts as low, and where the value is kept."""

    LOW: Final = 0.6
    PROPERTY: Final = "ocr_confidence"
