import re
from typing import Final
from xml.etree.ElementTree import Element

from ParserService.Infrastructure.Extraction.WordTag import WordTag


class DocxStyleReader:
    """Reads ``styles.xml``: which paragraph styles are headings (and their level) or lists."""

    HEADING: Final = re.compile(r"^heading ([1-9])$")
    TITLE: Final = "title"
    LIST_PREFIX: Final = "list"

    def heading_levels(self, styles: Element | None) -> dict[str, int]:
        """Map style ids to heading levels.

        Args:
            styles: The root of ``styles.xml``, or ``None`` when the part is missing.

        Returns:
            Heading level per style id; ``Title`` counts as level 1.
        """
        levels: dict[str, int] = {}
        for style_id, name in self._names(styles):
            match = self.HEADING.match(name)
            if match or name == self.TITLE:
                levels[style_id] = int(match.group(1)) if match else 1
        return levels

    def list_styles(self, styles: Element | None) -> frozenset[str]:
        """Find the paragraph styles that make a paragraph a list item.

        Args:
            styles: The root of ``styles.xml``, or ``None``.

        Returns:
            Ids of styles whose name starts with "list".
        """
        names = self._names(styles)
        return frozenset(style for style, name in names if name.startswith(self.LIST_PREFIX))

    @staticmethod
    def _names(styles: Element | None) -> list[tuple[str, str]]:
        if styles is None:
            return []
        found = []
        for style in styles.iter(WordTag.STYLE):
            name = style.find(WordTag.NAME)
            label = "" if name is None else name.get(WordTag.VAL, "")
            found.append((style.get(WordTag.STYLE_ID, ""), label.strip().casefold()))
        return found
