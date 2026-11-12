import zipfile
from pathlib import Path
from typing import Final


class SamplePptx:
    """Writes small synthetic PPTX packages by hand. Fixed timestamps keep them byte-identical."""

    P: Final = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    A: Final = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    R: Final = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    PACKAGE: Final = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    STAMP: Final = (2026, 1, 1, 0, 0, 0)

    def normal(self, path: Path) -> Path:
        """Three slides: title and bullets, a table and a picture, and a broken slide."""
        first = (
            self._shape("title", ("Synthetic deck",))
            + self._shape("body", ("First point", "Second point"))
            + self._shape(None, ("Free text box",))
        )
        second = self._shape("title", ("Numbers",)) + self._table() + self._picture()
        slides = (self._slide(first), self._slide(second), "<p:sld")
        return self._write(path, slides)

    def empty(self, path: Path) -> Path:
        """A presentation without slides."""
        return self._write(path, ())

    def corrupted(self, path: Path) -> Path:
        """A package whose presentation part is not well-formed XML."""
        with zipfile.ZipFile(path, "w") as package:
            package.writestr(zipfile.ZipInfo("ppt/presentation.xml", self.STAMP), "<p:presentation")
        return path

    def _shape(self, role: str | None, lines: tuple[str, ...]) -> str:
        placeholder = "" if role is None else f'<p:nvPr><p:ph type="{role}"/></p:nvPr>'
        paragraphs = "".join(f"<a:p><a:r><a:t>{line}</a:t></a:r></a:p>" for line in lines)
        return f"<p:sp><p:nvSpPr>{placeholder}</p:nvSpPr><p:txBody>{paragraphs}</p:txBody></p:sp>"

    @staticmethod
    def _cell(text: str) -> str:
        return f"<a:tc><a:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></a:txBody></a:tc>"

    def _table(self) -> str:
        rows = (("Metric", "Value"), ("Pages", "12"))
        body = "".join("<a:tr>" + "".join(map(self._cell, row)) + "</a:tr>" for row in rows)
        return (
            '<p:graphicFrame><a:graphic><a:graphicData><a:tbl><a:tblPr firstRow="1"/>'
            f"{body}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>"
        )

    @staticmethod
    def _picture() -> str:
        properties = '<p:cNvPr id="4" name="Chart" descr="Synthetic chart"/>'
        return f"<p:pic><p:nvPicPr>{properties}</p:nvPicPr></p:pic>"

    def _slide(self, shapes: str) -> str:
        return f"<p:sld {self.P} {self.A}><p:cSld><p:spTree>{shapes}</p:spTree></p:cSld></p:sld>"

    def _write(self, path: Path, slides: tuple[str, ...]) -> Path:
        numbers = range(1, len(slides) + 1)
        ids = "".join(f'<p:sldId id="{256 + n}" r:id="rId{n}"/>' for n in numbers)
        rels = "".join(f'<Relationship Id="rId{n}" Target="slides/slide{n}.xml"/>' for n in numbers)
        presentation = f"<p:presentation {self.P} {self.R}><p:sldIdLst>{ids}</p:sldIdLst>"
        relationships = f"<Relationships {self.PACKAGE}>{rels}</Relationships>"
        parts = {
            "ppt/presentation.xml": presentation + "</p:presentation>",
            "ppt/_rels/presentation.xml.rels": relationships,
        }
        parts |= {f"ppt/slides/slide{n}.xml": xml for n, xml in enumerate(slides, 1)}
        with zipfile.ZipFile(path, "w") as package:
            for name, xml in parts.items():
                package.writestr(zipfile.ZipInfo(name, self.STAMP), xml)
        return path
