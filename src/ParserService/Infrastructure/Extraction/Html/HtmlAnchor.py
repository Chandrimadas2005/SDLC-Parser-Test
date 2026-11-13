from dataclasses import dataclass, replace
from typing import Self

from ParserService.Domain.Documents.Locator import Locator


@dataclass(frozen=True, slots=True)
class HtmlAnchor:
    """The block that locators are currently measured against.

    HTML locators use the block number as the paragraph and character offsets into
    the document's extracted text: every block's text, in reading order, joined by
    one newline. ``cursor`` is how far into this block's text the last inline element
    was found, so repeated link texts are located one after the other.
    """

    paragraph: int
    start: int
    text: str
    cursor: int = 0

    @classmethod
    def before_first(cls) -> Self:
        """The position before the first block of a document."""
        return cls(paragraph=0, start=0, text="")

    def following(self, text: str) -> Self:
        """The anchor for the next block, which holds the given text.

        Args:
            text: The next block's text.

        Returns:
            The next block's anchor.
        """
        start = self.start + len(self.text) + 1 if self.paragraph else 0
        return type(self)(self.paragraph + 1, start, text)

    def locator(self) -> Locator:
        """Point at this whole block."""
        return Locator.for_text(self.paragraph, self.start, self.start + len(self.text))

    def locate(self, inner: str) -> tuple[Locator, Self]:
        """Point at a piece of text inside this block, such as a link's text.

        Args:
            inner: The text to find, searched after the previous find.

        Returns:
            Its locator, or the whole block's when it is not found, and the moved anchor.
        """
        found = self.text.find(inner, self.cursor) if inner else -1
        if found < 0:
            return self.locator(), self
        begin = self.start + found
        located = Locator.for_text(self.paragraph, begin, begin + len(inner))
        return located, replace(self, cursor=found + len(inner))
