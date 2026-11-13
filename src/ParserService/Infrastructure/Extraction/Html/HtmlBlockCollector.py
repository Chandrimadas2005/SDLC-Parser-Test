from dataclasses import replace

from ParserService.Infrastructure.Extraction.Html.HtmlBlock import HtmlBlock
from ParserService.Infrastructure.Extraction.Html.HtmlBlockStyle import HtmlBlockStyle
from ParserService.Infrastructure.Extraction.Html.HtmlReading import HtmlReading


class HtmlBlockCollector:
    """Gathers the blocks of one HTML document while its tree is walked.

    Text arrives in small pieces (text nodes and inline elements) and is held until
    the enclosing block ends; ``flush`` then turns it into one block with its
    whitespace collapsed, followed by the links and images found inside it. One
    collector serves exactly one document.
    """

    def __init__(self) -> None:
        self._blocks: list[HtmlBlock] = []
        self._text: list[str] = []
        self._inline: list[HtmlBlock] = []
        self._skipped: list[int] = []
        self._paragraphs = 0

    def add_text(self, text: str) -> None:
        """Add a piece of text to the block being collected.

        Args:
            text: Text as it appears in the document.
        """
        self._text.append(text)

    def add_inline(self, block: HtmlBlock) -> None:
        """Add a link or image found inside the block being collected.

        Args:
            block: The link or image, marked inline.
        """
        self._inline.append(block)

    def add_block(self, block: HtmlBlock) -> None:
        """Add a finished block, such as a table, after the current text was flushed.

        Args:
            block: The finished block.
        """
        self._append(block)

    def skip(self) -> None:
        """Record an element that was skipped and never run."""
        self._skipped.append(self._paragraphs + 1)

    def flush(self, style: HtmlBlockStyle) -> None:
        """End the block being collected, turning its text into one block.

        Links and images found inside it follow it. When it has no text, they become
        blocks of their own.

        Args:
            style: What the collected text becomes.
        """
        text = " ".join("".join(self._text).split())
        if text:
            self._append(HtmlBlock(style.kind, text, style.level))
        for block in self._inline:
            self._append(block if text else replace(block, inline=False))
        self._text.clear()
        self._inline.clear()

    def reading(self) -> HtmlReading:
        """Everything collected so far.

        Returns:
            The blocks in reading order and the skipped elements.
        """
        return HtmlReading(tuple(self._blocks), tuple(self._skipped))

    def _append(self, block: HtmlBlock) -> None:
        self._blocks.append(block)
        self._paragraphs += 0 if block.inline else 1
