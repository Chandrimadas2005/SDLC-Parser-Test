from enum import StrEnum


class PdfLibrary(StrEnum):
    """The three PDF libraries the brief asks to compare in Phase 2 (section 2.6)."""

    PYPDF = "pypdf"
    PDFPLUMBER = "pdfplumber"
    PYPDFIUM2 = "pypdfium2"
