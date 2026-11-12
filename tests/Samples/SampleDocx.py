import zipfile
from pathlib import Path
from typing import Final


class SampleDocx:
    """Writes small synthetic DOCX packages by hand. Fixed timestamps keep them byte-identical."""

    W: Final = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    STAMP: Final = (2026, 1, 1, 0, 0, 0)

    def normal(self, path: Path) -> Path:
        """Headings, a list, a marked and an unmarked table, a comment and tracked changes."""
        body = (
            self._p("Synthetic report", "Title")
            + self._p("Introduction", "Heading1")
            + '<w:p><w:commentRangeStart w:id="0"/><w:r><w:t>Kept text</w:t></w:r>'
            '<w:ins w:id="1"><w:r><w:t xml:space="preserve"> and inserted</w:t></w:r></w:ins>'
            '<w:del w:id="2"><w:r><w:delText> and deleted</w:delText></w:r></w:del>'
            "<w:r><w:t>.</w:t></w:r></w:p>"
            + "<w:p/>"
            + self._p("First bullet", "ListBullet")
            + '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr>'
            "<w:r><w:t>Numbered item</w:t></w:r></w:p>"
            + self._p("Details", "Heading2")
            + self._table((("ID", "Owner"), ("REQ-1", "Team A")), marked=True)
            + self._table((("a", "a"), ("1", "2")), marked=False)
        )
        return self._write(path, body, comments=True)

    def empty(self, path: Path) -> Path:
        """A document whose body has no content."""
        return self._write(path, "", comments=False)

    def corrupted(self, path: Path) -> Path:
        """A DOCX package whose main part is not well-formed XML."""
        with zipfile.ZipFile(path, "w") as package:
            package.writestr(zipfile.ZipInfo("word/document.xml", self.STAMP), "<w:document")
        return path

    @staticmethod
    def _p(text: str, style: str) -> str:
        return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'

    @staticmethod
    def _table(rows: tuple[tuple[str, ...], ...], *, marked: bool) -> str:
        header = "<w:trPr><w:tblHeader/></w:trPr>" if marked else ""
        cells = [
            "".join(f"<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>" for cell in row)
            for row in rows
        ]
        first, *rest = cells
        return (
            f"<w:tbl><w:tr>{header}{first}</w:tr>"
            + "".join(f"<w:tr>{r}</w:tr>" for r in rest)
            + "</w:tbl>"
        )

    def _write(self, path: Path, body: str, *, comments: bool) -> Path:
        parts = {
            "word/document.xml": f"<w:document {self.W}><w:body>{body}</w:body></w:document>",
            "word/styles.xml": f"<w:styles {self.W}>{self._styles()}</w:styles>",
        }
        if comments:
            parts["word/comments.xml"] = (
                f'<w:comments {self.W}><w:comment w:id="0"><w:p><w:r>'
                "<w:t>Synthetic reviewer note</w:t></w:r></w:p></w:comment></w:comments>"
            )
        with zipfile.ZipFile(path, "w") as package:
            for name, xml in parts.items():
                package.writestr(zipfile.ZipInfo(name, self.STAMP), xml)
        return path

    @staticmethod
    def _styles() -> str:
        styles: tuple[tuple[str, str], ...] = (
            ("Title", "Title"),
            ("Heading1", "heading 1"),
            ("Heading2", "heading 2"),
            ("ListBullet", "List Bullet"),
        )
        return "".join(
            f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/></w:style>'
            for sid, name in styles
        )
