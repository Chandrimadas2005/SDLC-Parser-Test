import io
import zipfile
from email.message import EmailMessage
from pathlib import Path

from tests.Samples.SampleDocx import SampleDocx


class SampleContainers:
    """Synthetic ZIP archives and e-mails holding other synthetic files."""

    def archive(self, path: Path) -> Path:
        """An archive with a Markdown file, a CSV, a DOCX, a nested ZIP and a zip-slip name."""
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as nested:
            nested.writestr("deep/notes.txt", "Nested synthetic note.\n")
        docx = SampleDocx().normal(path.with_suffix(".tmp.docx")).read_bytes()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("guide.md", "# Synthetic guide\n\nFirst paragraph.\n")
            archive.writestr("data/tasks.csv", "Task ID,Owner\nT-101,Asha\nT-102,Ravi\n")
            archive.writestr("report.docx", docx)
            archive.writestr("inner.zip", inner.getvalue())
            archive.writestr("../escape.txt", "Synthetic text with an unsafe name.\n")
        return path

    def nested(self, path: Path, levels: int) -> Path:
        """A text file wrapped in ``levels`` archives, one inside the other."""
        content, name = b"Innermost synthetic text.\n", "note.txt"
        for level in range(levels):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr(name, content)
            content, name = buffer.getvalue(), f"level-{level}.zip"
        path.write_bytes(content)
        return path

    def email(self, path: Path, *, html_only: bool = False) -> Path:
        """An e-mail with headers, a body and a CSV attachment."""
        message = EmailMessage()
        message["Subject"] = "Synthetic status update"
        message["From"] = "Asha <asha@example.invalid>"
        message["To"] = "Ravi <ravi@example.invalid>"
        if html_only:
            message.set_content(
                "<html><body><p>Hello from HTML.</p><p>Second line.</p></body></html>",
                subtype="html",
            )
        else:
            message.set_content("Hello team.\n\nThe pilot starts next week.\n")
        message.add_attachment(
            b"Task ID,Owner\nT-101,Asha\n", maintype="text", subtype="csv", filename="tasks.csv"
        )
        path.write_bytes(bytes(message))
        return path
