import re
from typing import Final

from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Infrastructure.Extraction.TextBlock import TextBlock


class PlainTextBlockSplitter:
    """Splits plain text into paragraphs: runs of non-blank lines between blank lines."""

    PARAGRAPH: Final = re.compile(r"[^\n]*\S[^\n]*(?:\n[^\n]*\S[^\n]*)*")

    def blocks(self, text: str) -> list[TextBlock]:
        """Find the paragraphs of a text.

        Args:
            text: The decoded file content.

        Returns:
            One paragraph block per run of non-blank lines, in reading order.
        """
        return [
            self._block(text, match.start(), match.end()) for match in self.PARAGRAPH.finditer(text)
        ]

    @staticmethod
    def _block(text: str, start: int, end: int) -> TextBlock:
        raw = text[start:end]
        first = start + len(raw) - len(raw.lstrip())
        last = start + len(raw.rstrip())
        return TextBlock(ElementKind.PARAGRAPH, text[first:last], first, last)
