from dataclasses import dataclass

from ParserService.Domain.Documents.OutlineEntry import OutlineEntry
from ParserService.Infrastructure.Extraction.PdfPageText import PdfPageText


@dataclass(frozen=True, slots=True)
class PdfContent:
    """What was read from a PDF: the text of every page and its bookmarks as an outline."""

    pages: tuple[PdfPageText, ...]
    outline: tuple[OutlineEntry, ...]
