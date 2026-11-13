from typing import Final

from bs4.element import Tag

from ParserService.Domain.Documents.ImageSource import ImageSource
from ParserService.Infrastructure.Extraction.Html.HtmlAttribute import HtmlAttribute


class HtmlImageReader:
    """Reads an ``<img>``'s source and declared size (schema 1.2).

    The source is kept as written and never fetched. Inline ``data:`` images and
    script URLs are left out: the first can be megabytes of encoded bytes, the second
    is not an image. Width and height are kept only when given in whole pixels;
    sizes such as ``50%`` are left out.
    """

    LEFT_OUT_SCHEMES: Final = ("data:", "javascript:", "vbscript:")
    MAX_SIZE: Final = 100_000

    def read(self, tag: Tag) -> ImageSource | None:
        """Read an image element.

        Args:
            tag: The ``img`` element.

        Returns:
            The source and size, or ``None`` when the image states none of them.
        """
        source = self._source(HtmlAttribute.SRC.of(tag))
        width = self._pixels(HtmlAttribute.WIDTH.of(tag))
        height = self._pixels(HtmlAttribute.HEIGHT.of(tag))
        if source is None and width is None and height is None:
            return None
        return ImageSource(source, width, height)

    def _source(self, value: str) -> str | None:
        compact = "".join(char for char in value if char.isprintable() and not char.isspace())
        if not compact or compact.lower().startswith(self.LEFT_OUT_SCHEMES):
            return None
        return value

    def _pixels(self, value: str) -> int | None:
        digits = value.removesuffix("px")
        if not digits.isdigit() or not 0 < int(digits) <= self.MAX_SIZE:
            return None
        return int(digits)
