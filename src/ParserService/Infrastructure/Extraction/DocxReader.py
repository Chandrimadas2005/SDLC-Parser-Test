import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.DocxContent import DocxContent
from ParserService.Infrastructure.Extraction.DocxParagraph import DocxParagraph
from ParserService.Infrastructure.Extraction.DocxParagraphReader import DocxParagraphReader
from ParserService.Infrastructure.Extraction.DocxPart import DocxPart
from ParserService.Infrastructure.Extraction.DocxStyleReader import DocxStyleReader
from ParserService.Infrastructure.Extraction.DocxTable import DocxTable
from ParserService.Infrastructure.Extraction.WordTag import WordTag


class DocxReader:
    """Reads a DOCX package directly as XML, with defusedxml (brief, sections 2.2 and 2.5).

    Only the body, styles and comments parts are read. Macros and embedded objects
    are never opened, and nothing is extracted to disk.
    """

    def __init__(self, styles: DocxStyleReader) -> None:
        self._styles = styles

    def read(self, path: Path) -> Result[DocxContent, FailureReason]:
        """Read the body blocks, comments and tracked changes of a DOCX file.

        Args:
            path: The DOCX file.

        Returns:
            The content, or ``corrupted_file`` when the package or its XML is broken.
        """
        try:
            with zipfile.ZipFile(path) as package:
                return Result.ok(self._content(package))
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, OSError):
            return Result.err(FailureReason.CORRUPTED_FILE)

    def _content(self, package: zipfile.ZipFile) -> DocxContent:
        document = ElementTree.fromstring(package.read(DocxPart.DOCUMENT))
        styles = self._optional(package, DocxPart.STYLES)
        reader = DocxParagraphReader(
            self._styles.heading_levels(styles), self._styles.list_styles(styles)
        )
        body = document.find(WordTag.BODY)
        blocks = () if body is None else tuple(self._block(reader, node) for node in body)
        comments = self._comments(reader, self._optional(package, DocxPart.COMMENTS))
        inserted = sum(1 for _ in document.iter(WordTag.INSERTION))
        deleted = sum(1 for _ in document.iter(WordTag.DELETION))
        kept = tuple(block for block in blocks if block is not None)
        return DocxContent(kept, comments, inserted, deleted)

    @staticmethod
    def _optional(package: zipfile.ZipFile, part: DocxPart) -> Element | None:
        if part not in package.namelist():
            return None
        return ElementTree.fromstring(package.read(part))

    def _block(
        self, reader: DocxParagraphReader, node: Element
    ) -> DocxParagraph | DocxTable | None:
        if node.tag == WordTag.PARAGRAPH:
            return reader.read(node)
        if node.tag == WordTag.TABLE:
            return self._table(reader, node)
        return None

    @staticmethod
    def _table(reader: DocxParagraphReader, table: Element) -> DocxTable:
        rows = tuple(
            tuple(reader.text(cell) for cell in row.iter(WordTag.CELL))
            for row in table.iter(WordTag.ROW)
        )
        first = table.find(WordTag.ROW)
        marked = first is not None and first.find(f".//{WordTag.TABLE_HEADER}") is not None
        return DocxTable(rows, marked)

    @staticmethod
    def _comments(reader: DocxParagraphReader, comments: Element | None) -> dict[str, str]:
        if comments is None:
            return {}
        return {
            comment.get(WordTag.ID, ""): reader.text(comment)
            for comment in comments.iter(WordTag.COMMENT)
        }
