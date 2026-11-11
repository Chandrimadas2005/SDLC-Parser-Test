from pathlib import Path

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
