import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Final

from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Infrastructure.Extraction.TextBlock import TextBlock

type _Handler = Callable[["_Scan", int, re.Match[str]], None]


@dataclass(slots=True)
class _Scan:
    """Working state while one Markdown text is read, line by line."""

    text: str
    blocks: list[TextBlock]
    paragraph: list[tuple[int, str]]
    fence: list[tuple[int, str]] | None


class MarkdownBlockReader:
    """Reads Markdown into blocks: headings, list items, paragraphs and code blocks.

    ATX headings (``#`` to ``######``) keep their level. Each list item is its own
    block. Fenced code blocks become one paragraph holding the code. Inline markup
    such as ``*emphasis*`` is kept as written.
    """

    HEADING: Final = re.compile(r" {0,3}(#{1,6})[ \t]+(.*?\S)[ \t#]*$")
    LIST_ITEM: Final = re.compile(r"[ \t]*(?:[-*+]|\d{1,9}[.)])[ \t]+(.*\S)")
    FENCE: Final = re.compile(r" {0,3}(?:```|~~~)")

    def blocks(self, text: str) -> list[TextBlock]:
        """Find the blocks of a Markdown text.

        Args:
            text: The decoded file content.

        Returns:
            The blocks in reading order.
        """
        scan = _Scan(text, [], [], None)
        for start, line in self._lines(text):
            self._feed(scan, start, line)
        self._close_fence(scan)
        self._flush_paragraph(scan)
        return scan.blocks

    @staticmethod
    def _lines(text: str) -> Iterator[tuple[int, str]]:
        offset = 0
        for raw in text.splitlines(keepends=True):
            yield offset, raw.rstrip("\r\n")
            offset += len(raw)

    def _feed(self, scan: _Scan, start: int, line: str) -> None:
        if scan.fence is not None:
            self._feed_fence(scan, start, line)
            return
        if not line.strip():
            self._flush_paragraph(scan)
            return
        if not self._starts_block(scan, start, line):
            scan.paragraph.append((start, line))

    def _starts_block(self, scan: _Scan, start: int, line: str) -> bool:
        handlers: tuple[
            tuple[re.Pattern[str], Callable[[_Scan, int, re.Match[str]], None]], ...
        ] = (
            (self.FENCE, self._open_fence),
            (self.HEADING, self._heading),
            (self.LIST_ITEM, self._list_item),
        )
        for pattern, handler in handlers:
            match = pattern.match(line)
            if match:
                self._flush_paragraph(scan)
                handler(scan, start, match)
                return True
        return False

    @staticmethod
    def _open_fence(scan: _Scan, start: int, match: re.Match[str]) -> None:
        scan.fence = [(start, match.string)]

    def _feed_fence(self, scan: _Scan, start: int, line: str) -> None:
        fence = scan.fence if scan.fence is not None else []
        fence.append((start, line))
        if self.FENCE.match(line):
            self._close_fence(scan)

    @staticmethod
    def _close_fence(scan: _Scan) -> None:
        if not scan.fence:
            return
        (first, _), *body = scan.fence
        last_start, last_line = scan.fence[-1]
        code = "\n".join(line for _, line in body if not MarkdownBlockReader.FENCE.match(line))
        end = last_start + len(last_line.rstrip())
        scan.blocks.append(TextBlock(ElementKind.PARAGRAPH, code, first, end))
        scan.fence = None

    @staticmethod
    def _heading(scan: _Scan, start: int, match: re.Match[str]) -> None:
        span = (start + match.start(2), start + match.end(2))
        level = len(match.group(1))
        scan.blocks.append(TextBlock(ElementKind.HEADING, match.group(2), *span, level=level))

    @staticmethod
    def _list_item(scan: _Scan, start: int, match: re.Match[str]) -> None:
        span = (start + match.start(1), start + match.end(1))
        scan.blocks.append(TextBlock(ElementKind.LIST_ITEM, match.group(1), *span))

    @staticmethod
    def _flush_paragraph(scan: _Scan) -> None:
        if not scan.paragraph:
            return
        first = (
            scan.paragraph[0][0] + len(scan.paragraph[0][1]) - len(scan.paragraph[0][1].lstrip())
        )
        last_start, last_line = scan.paragraph[-1]
        end = last_start + len(last_line.rstrip())
        content = " ".join(line.strip() for _, line in scan.paragraph)
        scan.blocks.append(TextBlock(ElementKind.PARAGRAPH, content, first, end))
        scan.paragraph = []
