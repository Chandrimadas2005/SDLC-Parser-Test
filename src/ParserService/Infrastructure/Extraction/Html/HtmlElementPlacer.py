from collections.abc import Sequence

from ParserService.Domain.Documents.Element import Element
from ParserService.Domain.Documents.ElementId import ElementId
from ParserService.Domain.Documents.Locator import Locator
from ParserService.Infrastructure.Extraction.Html.HtmlAnchor import HtmlAnchor
from ParserService.Infrastructure.Extraction.Html.HtmlBlock import HtmlBlock


class HtmlElementPlacer:
    """Gives every HTML block its stable element id and its source locator.

    Ids follow reading order. Each block gets the next paragraph number and its
    character span in the extracted text; a link or image inside a block points at
    its own text within that block.
    """

    def place(self, blocks: Sequence[HtmlBlock]) -> tuple[Element, ...]:
        """Turn blocks into elements.

        Args:
            blocks: The blocks in reading order.

        Returns:
            The elements, in the same order.
        """
        elements: list[Element] = []
        anchor = HtmlAnchor.before_first()
        for position, block in enumerate(blocks, 1):
            locator, anchor = self._locate(block, anchor)
            element_id = ElementId.at(position)
            elements.append(self._element(element_id, block, locator))
        return tuple(elements)

    @staticmethod
    def _locate(block: HtmlBlock, anchor: HtmlAnchor) -> tuple[Locator, HtmlAnchor]:
        if block.inline:
            return anchor.locate(block.text)
        following = anchor.following(block.text)
        return following.locator(), following

    @staticmethod
    def _element(element_id: ElementId, block: HtmlBlock, locator: Locator) -> Element:
        return Element(
            element_id,
            block.kind,
            locator,
            block.text or None,
            block.level,
            block.table,
            href=block.href,
            image=block.image,
        )
