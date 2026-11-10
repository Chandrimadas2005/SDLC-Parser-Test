from enum import StrEnum


class WarningCode(StrEnum):
    """Why something was skipped, guessed or repaired (brief, sections 2.2 and 2.5).

    Every warning carries one of these codes, so no failure is ever hidden.
    """

    EXTENSION_MISMATCH = "extension_mismatch"
    ENCODING_GUESSED = "encoding_guessed"
    PAGE_UNREADABLE = "page_unreadable"
    SHEET_UNREADABLE = "sheet_unreadable"
    SLIDE_UNREADABLE = "slide_unreadable"
    ELEMENT_SKIPPED = "element_skipped"
    FILE_REPAIRED = "file_repaired"
    OCR_APPLIED = "ocr_applied"
    OCR_LOW_CONFIDENCE = "ocr_low_confidence"
    HEADER_ROW_GUESSED = "header_row_guessed"
    SUMMARY_UNAVAILABLE = "summary_unavailable"
