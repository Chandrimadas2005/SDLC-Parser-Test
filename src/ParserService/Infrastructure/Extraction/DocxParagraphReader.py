from collections.abc import Mapping
from typing import Final
from xml.etree.ElementTree import Element

from ParserService.Infrastructure.Extraction.DocxParagraph import DocxParagraph
from ParserService.Infrastructure.Extraction.WordTag import WordTag


class DocxParagraphReader:
    """Reads one ``w:p``: accepted text, heading level, list flag and comment anchors.

    Inserted text is kept and deleted text (``w:delText``) is dropped, so the text is
    what the document reads like with every tracked change accepted.
    """

    OUTLINE_LEVELS: Final = frozenset("012345678")
    BREAKS: Final = {WordTag.TAB: "\t", WordTag.BREAK: "\n"}

    def __init__(self, headings: Mapping[str, int], lists: frozenset[str]) -> None:
        self._headings = headings
        self._lists = lists

    def read(self, paragraph: Element) -> DocxParagraph:
        """Read a paragraph.

        Args:
            paragraph: A ``w:p`` element.

        Returns:
            The paragraph's text and structure.
        """
        style = self._style(paragraph)
        comments = tuple(mark.get(WordTag.ID, "") for mark in paragraph.iter(WordTag.COMMENT_START))
        is_list = paragraph.find(f".//{WordTag.NUMBERING}") is not None or style in self._lists
        return DocxParagraph(self.text(paragraph), self._level(paragraph, style), is_list, comments)

    def text(self, element: Element) -> str:
        """The accepted text inside an element: text runs, tabs and line breaks.

        Args:
            element: A paragraph, cell or comment element.

        Returns:
            The text, with surrounding whitespace removed.
        """
        parts = [self._piece(node) for node in element.iter()]
        return "".join(parts).strip()

    def _piece(self, node: Element) -> str:
        if node.tag == WordTag.TEXT:
            return node.text or ""
        return self.BREAKS.get(WordTag(node.tag), "") if node.tag in self.BREAKS else ""

    @staticmethod
    def _style(paragraph: Element) -> str:
        style = paragraph.find(f".//{WordTag.PARAGRAPH_STYLE}")
        return "" if style is None else style.get(WordTag.VAL, "")

    def _level(self, paragraph: Element, style: str) -> int | None:
        outline = paragraph.find(f".//{WordTag.OUTLINE_LEVEL}")
        value = "" if outline is None else outline.get(WordTag.VAL, "")
        if value in self.OUTLINE_LEVELS:
            return int(value) + 1
        return self._headings.get(style)
