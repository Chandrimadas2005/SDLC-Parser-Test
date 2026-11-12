from collections.abc import Iterator
from typing import Final
from xml.etree.ElementTree import Element

from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Infrastructure.Extraction.PptxPart import PptxPart
from ParserService.Infrastructure.Extraction.PptxSlide import PptxSlide
from ParserService.Infrastructure.Extraction.SlideBlock import SlideBlock
from ParserService.Infrastructure.Extraction.SlideTag import SlideTag


class PptxSlideReader:
    """Reads one slide's XML: title, text boxes, bullet lists, tables and image alt text.

    Shapes are read in the slide's own order, including shapes inside groups. The
    first paragraph of a title placeholder is the slide title; paragraphs of a body
    placeholder are list items; any other text is a paragraph.
    """

    TITLES: Final = frozenset({"title", "ctrTitle"})
    BODY: Final = "body"
    BREAKS: Final = {SlideTag.BREAK: "\n"}

    def read(self, slide: Element, number: int) -> PptxSlide:
        """Read a slide.

        Args:
            slide: The root of the slide part.
            number: One-based slide number.

        Returns:
            The slide with its title and items in order.
        """
        blocks: list[SlideBlock] = []
        title: str | None = None
        for node in slide.iter():
            for block in self._blocks(node):
                is_title = block.kind is ElementKind.HEADING and title is None
                title = block.text if is_title else title
                blocks.append(block)
        return PptxSlide(number, title, tuple(blocks), readable=True)

    def _blocks(self, node: Element) -> Iterator[SlideBlock]:
        if node.tag == SlideTag.SHAPE:
            yield from self._shape(node)
        elif node.tag == SlideTag.FRAME:
            yield from self._table(node)
        elif node.tag == SlideTag.PICTURE:
            yield self._picture(node)

    def _shape(self, shape: Element) -> Iterator[SlideBlock]:
        placeholder = shape.find(f".//{SlideTag.PLACEHOLDER}")
        role = "" if placeholder is None else placeholder.get(PptxPart.TYPE, self.BODY)
        texts = [self._text(p) for p in shape.iter(SlideTag.PARAGRAPH)]
        for text in (t for t in texts if t):
            yield SlideBlock(self._kind(role), text)

    def _kind(self, role: str) -> ElementKind:
        if role in self.TITLES:
            return ElementKind.HEADING
        return ElementKind.LIST_ITEM if role == self.BODY else ElementKind.PARAGRAPH

    def _table(self, frame: Element) -> Iterator[SlideBlock]:
        table = frame.find(f".//{SlideTag.TABLE}")
        if table is None:
            return
        rows = tuple(
            tuple(self._text(cell) for cell in row.iter(SlideTag.CELL))
            for row in table.iter(SlideTag.ROW)
        )
        properties = table.find(SlideTag.TABLE_PROPERTIES)
        flag = "" if properties is None else properties.get(PptxPart.FIRST_ROW, "")
        yield SlideBlock(ElementKind.TABLE, None, rows, header_marked=flag == PptxPart.ENABLED)

    @staticmethod
    def _picture(picture: Element) -> SlideBlock:
        properties = picture.find(f".//{SlideTag.DRAWING_PROPERTIES}")
        alt = None if properties is None else properties.get(PptxPart.DESCRIPTION) or None
        return SlideBlock(ElementKind.IMAGE, alt)

    def _text(self, element: Element) -> str:
        parts = [self._piece(node) for node in element.iter()]
        return "".join(parts).strip()

    def _piece(self, node: Element) -> str:
        if node.tag == SlideTag.TEXT:
            return node.text or ""
        return "\n" if node.tag == SlideTag.BREAK else ""
