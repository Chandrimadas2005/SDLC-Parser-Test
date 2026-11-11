from pathlib import Path
from typing import TYPE_CHECKING

import pdfplumber
import pypdfium2
from pypdf import PdfReader

from tools.PdfComparison.PdfLibrary import PdfLibrary

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class PdfTextExtraction:
    """Extracts the text of every page with one of the compared libraries."""

    def pages(self, library: PdfLibrary, path: Path) -> list[str]:
        """Extract page texts.

        Args:
            library: Which library to use.
            path: The PDF to read.

        Returns:
            One text per page, in page order.
        """
        readers: Mapping[PdfLibrary, Callable[[Path], list[str]]] = {
            PdfLibrary.PYPDF: self._pypdf,
            PdfLibrary.PDFPLUMBER: self._pdfplumber,
            PdfLibrary.PYPDFIUM2: self._pypdfium2,
        }
        return readers[library](path)

    @staticmethod
    def _pypdf(path: Path) -> list[str]:
        return [page.extract_text() or "" for page in PdfReader(path).pages]

    @staticmethod
    def _pdfplumber(path: Path) -> list[str]:
        with pdfplumber.open(path) as document:
            return [page.extract_text() or "" for page in document.pages]

    @staticmethod
    def _pypdfium2(path: Path) -> list[str]:
        document = pypdfium2.PdfDocument(path)
        texts = [page.get_textpage().get_text_range() for page in document]
        document.close()
        return texts
