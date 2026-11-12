from pathlib import Path
from typing import Final

import pypdfium2

from ParserService.Domain.Documents.Locator import Locator
from ParserService.Domain.Documents.OutlineEntry import OutlineEntry
from ParserService.Domain.Documents.OutlineKind import OutlineKind
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.PdfContent import PdfContent
from ParserService.Infrastructure.Extraction.PdfPageText import PdfPageText


class PdfReader:
    """Reads the text layer and bookmarks of a PDF with pypdfium2 (Google's PDFium).

    PDFium loads pages lazily, so a large file is never held in memory whole. A page
    that fails to load is reported as unreadable instead of failing the whole file.
    The page count is checked before any page is read: above ``max_pages`` the file
    is rejected with ``file_too_large`` (brief 2.5).
    Macros, scripts and embedded objects are never run: only text is read.
    """

    PASSWORD_ERROR: Final = 4

    def __init__(self, max_pages: int | None = None) -> None:
        self._max_pages = max_pages

    def read(self, path: Path) -> Result[PdfContent, FailureReason]:
        """Read every page and the outline.

        Args:
            path: The PDF to read.

        Returns:
            The content, ``password_protected`` for an encrypted file,
            ``corrupted_file`` when PDFium cannot open it, or ``file_too_large`` when
            it has more pages than allowed.
        """
        try:
            document = pypdfium2.PdfDocument(path)
        except pypdfium2.PdfiumError as error:
            return Result.err(self._failure(error))
        if self._max_pages is not None and len(document) > self._max_pages:
            document.close()
            return Result.err(FailureReason.FILE_TOO_LARGE)
        pages = tuple(self._page(document, index) for index in range(len(document)))
        outline = self._outline(document)
        document.close()
        return Result.ok(PdfContent(pages, outline))

    def _failure(self, error: pypdfium2.PdfiumError) -> FailureReason:
        if getattr(error, "err_code", None) == self.PASSWORD_ERROR:
            return FailureReason.PASSWORD_PROTECTED
        return FailureReason.CORRUPTED_FILE

    @staticmethod
    def _page(document: pypdfium2.PdfDocument, index: int) -> PdfPageText:
        try:
            page = document[index]
        except pypdfium2.PdfiumError:
            return PdfPageText(index + 1, None)
        text = str(page.get_textpage().get_text_range())
        page.close()
        return PdfPageText(index + 1, text)

    @staticmethod
    def _outline(document: pypdfium2.PdfDocument) -> tuple[OutlineEntry, ...]:
        entries: list[OutlineEntry] = []
        for bookmark in document.get_toc():
            destination = bookmark.get_dest()
            title = str(bookmark.get_title()).strip()
            if destination is None or not title:
                continue
            page = Locator.for_page(int(destination.get_index()) + 1)
            entries.append(OutlineEntry(OutlineKind.HEADING, title, page, int(bookmark.level) + 1))
        return tuple(entries)
