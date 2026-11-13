from enum import StrEnum

from bs4.element import Tag


class HtmlAttribute(StrEnum):
    """The HTML attributes the HTML extractor reads."""

    HREF = "href"
    ALT = "alt"
    SRC = "src"
    WIDTH = "width"
    HEIGHT = "height"
    LANG = "lang"
    NAME = "name"
    CONTENT = "content"
    COLSPAN = "colspan"
    ROWSPAN = "rowspan"

    def of(self, tag: Tag) -> str:
        """Read this attribute from an element, with its whitespace collapsed.

        Args:
            tag: The element.

        Returns:
            The attribute value, or an empty string when it is missing.
        """
        value = tag.get(self.value)
        return " ".join(value.split()) if isinstance(value, str) else ""
