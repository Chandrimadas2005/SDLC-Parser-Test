from pathlib import Path
from typing import Final

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from tools.PdfComparison.SyntheticPdf import SyntheticPdf


class SyntheticPdfFactory:
    """Writes PDFs with known, synthetic text: a heading, paragraphs and a small table.

    Words come from a fixed list in a fixed order, so every run produces the same
    files and the expected text of each page is known exactly. No real data.
    """

    WORDS: Final = (
        "parser",
        "locator",
        "element",
        "heading",
        "paragraph",
        "table",
        "column",
        "row",
        "sheet",
        "slide",
        "warning",
        "outline",
        "metric",
        "schema",
        "version",
        "status",
        "partial",
        "failed",
        "synthetic",
        "sample",
    )
    LINES_PER_PAGE: Final = 30
    WORDS_PER_LINE: Final = 10
    LEFT: Final = 50
    TOP: Final = 800
    LINE_HEIGHT: Final = 18

    def create(self, path: Path, page_count: int) -> SyntheticPdf:
        """Write a PDF with the given number of pages.

        Args:
            path: Where to write the file.
            page_count: How many pages to generate.

        Returns:
            The file and the words expected on each page.
        """
        canvas = Canvas(str(path), pagesize=A4)
        pages = tuple(self._page(canvas, number) for number in range(1, page_count + 1))
        canvas.save()
        return SyntheticPdf(path, pages)

    def _page(self, canvas: Canvas, number: int) -> tuple[str, ...]:
        lines = [f"Synthetic heading {number}"]
        lines += [self._line(number, row) for row in range(self.LINES_PER_PAGE)]
        lines += [f"ID{number} Status{number} Owner{number}"]
        for index, line in enumerate(lines):
            canvas.drawString(self.LEFT, self.TOP - index * self.LINE_HEIGHT, line)
        canvas.showPage()
        return tuple(word for line in lines for word in line.split())

    def _line(self, page: int, row: int) -> str:
        offset = page * self.LINES_PER_PAGE + row
        count = len(self.WORDS)
        return " ".join(self.WORDS[(offset + i) % count] for i in range(self.WORDS_PER_LINE))
