import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final
from xml.sax.saxutils import escape, quoteattr


class OdsPackage:
    """Writes small synthetic ODS packages as raw OpenDocument XML. No real data.

    Cells, rows and sheets are built as XML text, so tests control exactly what the
    extractor sees: repeats, merges, hidden styles, formulas, broken XML.
    """

    MIMETYPE: Final = b"application/vnd.oasis.opendocument.spreadsheet"
    NAMESPACES: Final = (
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
        'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
        'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/"'
    )
    ENCRYPTED_MANIFEST: Final = (
        b"<manifest:manifest><manifest:encryption-data/></manifest:manifest>"
    )

    def text(self, value: str, attributes: str = "") -> str:
        """A text cell."""
        start = f'<table:table-cell office:value-type="string" {attributes}>'
        return f"{start}{self._p(value)}</table:table-cell>"

    def number(self, value: str, formula: str = "") -> str:
        """A number cell, optionally the cached result of a formula."""
        extra = f" table:formula={quoteattr(formula)}" if formula else ""
        cell = f'office:value-type="float" office:value="{value}"{extra}'
        return f"<table:table-cell {cell}>{self._p(value)}</table:table-cell>"

    def typed(self, kind: str, attribute: str, value: str) -> str:
        """A cell of another value type, such as a date or a boolean."""
        cell = f'office:value-type="{kind}" office:{attribute}="{value}"'
        return f"<table:table-cell {cell}>{self._p(value)}</table:table-cell>"

    def empty(self, repeated: int = 1) -> str:
        """An empty cell, optionally repeated over several columns."""
        return f'<table:table-cell table:number-columns-repeated="{repeated}"/>'

    def covered(self, repeated: int = 1) -> str:
        """A cell hidden by a merged range."""
        return f'<table:covered-table-cell table:number-columns-repeated="{repeated}"/>'

    def row(self, cells: Sequence[str], repeated: int = 1) -> str:
        """A row of cells, optionally repeated."""
        start = f'<table:table-row table:number-rows-repeated="{repeated}">'
        return f"{start}{''.join(cells)}</table:table-row>"

    def sheet(self, name: str, rows: Sequence[str], style: str = "") -> str:
        """A sheet holding the given rows, optionally with a table style."""
        styled = f" table:style-name={quoteattr(style)}" if style else ""
        return f"<table:table table:name={quoteattr(name)}{styled}>{''.join(rows)}</table:table>"

    def content(self, sheets: Sequence[str], hidden_styles: Sequence[str] = ()) -> bytes:
        """The ``content.xml`` of a workbook with these sheets and hidden table styles."""
        styles = "".join(self._hidden_style(name) for name in hidden_styles)
        body = (
            f"<office:body><office:spreadsheet>{''.join(sheets)}</office:spreadsheet></office:body>"
        )
        root = f"<office:automatic-styles>{styles}</office:automatic-styles>{body}"
        return (
            f"<office:document-content {self.NAMESPACES}>{root}</office:document-content>".encode()
        )

    def write(self, path: Path, content: bytes, extra: Mapping[str, bytes] | None = None) -> Path:
        """Write a package with this content and any extra entries (manifest, meta)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(zipfile.ZipInfo("mimetype"), self.MIMETYPE)
            archive.writestr("content.xml", content, zipfile.ZIP_DEFLATED)
            for name, data in (extra or {}).items():
                archive.writestr(name, data, zipfile.ZIP_DEFLATED)
        return path

    def meta(self, fields: Mapping[str, str]) -> bytes:
        """A ``meta.xml`` holding the given qualified fields, such as ``dc:title``."""
        items = "".join(f"<{name}>{escape(value)}</{name}>" for name, value in fields.items())
        meta = f"<office:meta>{items}</office:meta>"
        return f"<office:document-meta {self.NAMESPACES}>{meta}</office:document-meta>".encode()

    @staticmethod
    def _p(value: str) -> str:
        return f"<text:p>{escape(value)}</text:p>"

    @staticmethod
    def _hidden_style(name: str) -> str:
        properties = '<style:table-properties table:display="false"/>'
        return f'<style:style style:name="{name}" style:family="table">{properties}</style:style>'
