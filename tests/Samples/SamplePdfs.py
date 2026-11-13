import io
from pathlib import Path

import pypdfium2
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.pdfgen.canvas import Canvas


class SamplePdfs:
    """Writes small synthetic PDFs for tests. ``invariant`` makes every run byte-identical."""

    def normal(self, path: Path) -> Path:
        """Two pages of text with bookmarks, then a page with no text layer."""
        canvas = Canvas(str(path), invariant=1)
        canvas.bookmarkPage("intro")
        canvas.addOutlineEntry("Introduction", "intro", level=0)
        lines = ("Introduction", "", "First paragraph, line one.", "First paragraph, line two.")
        self._write(canvas, lines)
        canvas.bookmarkPage("details")
        canvas.addOutlineEntry("Details", "details", level=1)
        self._write(canvas, ("Details of the synthetic sample.",))
        canvas.showPage()
        canvas.save()
        return path

    def encrypted(self, path: Path) -> Path:
        """A PDF that needs a password to open."""
        canvas = Canvas(str(path), encrypt=StandardEncryption("synthetic-secret", canPrint=0))
        self._write(canvas, ("Secret synthetic text.",))
        canvas.save()
        return path

    def corrupted(self, path: Path) -> Path:
        """A PDF cut off after its first bytes."""
        whole = self.normal(path.with_suffix(".whole.pdf")).read_bytes()
        path.write_bytes(whole[:300])
        return path

    @staticmethod
    def _write(canvas: Canvas, lines: tuple[str, ...]) -> None:
        for index, line in enumerate(lines):
            canvas.drawString(50, 800 - index * 15, line)
        canvas.showPage()

    def scanned(self, path: Path) -> Path:
        """Two pages: page 1 has a text layer, page 2 is only an image of printed text."""
        text_page = io.BytesIO()
        canvas = Canvas(text_page, pagesize=(595, 842))
        canvas.setFont("Helvetica", 28)
        canvas.drawString(60, 700, "Synthetic scanned invoice")
        canvas.drawString(60, 640, "Total amount 1250")
        canvas.save()
        picture = pypdfium2.PdfDocument(text_page.getvalue())[0].render(scale=200 / 72)
        document = pypdfium2.PdfDocument.new()
        self._text_page(document)
        page = document.new_page(595, 842)
        image = pypdfium2.PdfImage.new(document)
        image.set_bitmap(picture)
        image.set_matrix(pypdfium2.PdfMatrix().scale(595, 842))
        page.insert_obj(image)
        page.gen_content()
        document.save(path)
        return path

    @staticmethod
    def _text_page(document: pypdfium2.PdfDocument) -> None:
        source = io.BytesIO()
        canvas = Canvas(source, pagesize=(595, 842))
        canvas.drawString(72, 770, "Cover page with a text layer.")
        canvas.save()
        document.import_pages(pypdfium2.PdfDocument(source.getvalue()))
