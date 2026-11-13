from html.parser import HTMLParser
from typing import Final


class HtmlText(HTMLParser):
    """Turns an HTML e-mail body into plain text when no HTML extractor is installed.

    Block elements become line breaks; script and style content is dropped; nothing
    is fetched or run.
    """

    SKIPPED: Final = frozenset({"script", "style", "head"})
    BREAKS: Final = frozenset({"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skipping = 0

    def plain(self, html: str) -> str:
        """Return the visible text of an HTML fragment.

        Args:
            html: The HTML source.

        Returns:
            Its text, with blank lines between blocks.
        """
        self.feed(html)
        self.close()
        lines = (line.strip() for line in "".join(self._parts).splitlines())
        return "\n\n".join(line for line in lines if line)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: D102
        del attrs
        self._skipping += tag in self.SKIPPED
        self._parts.append("\n" if tag in self.BREAKS else "")

    def handle_endtag(self, tag: str) -> None:  # noqa: D102
        self._skipping -= tag in self.SKIPPED and self._skipping > 0
        self._parts.append("\n" if tag in self.BREAKS else "")

    def handle_data(self, data: str) -> None:  # noqa: D102
        if not self._skipping:
            self._parts.append(data)
