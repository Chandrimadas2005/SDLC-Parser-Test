from dataclasses import dataclass

from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Domain.Documents.ImageSource import ImageSource
from ParserService.Domain.Documents.Table import Table


@dataclass(frozen=True, slots=True)
class HtmlBlock:
    """One element found in an HTML document, before it gets its id and locator.

    ``inline`` marks a link or an image that sits inside the text of the block just
    before it; it is located inside that block's text instead of taking its own
    paragraph number. ``href`` and ``image`` carry a link's target and an image's
    source and declared size (schema 1.2).
    """

    kind: ElementKind
    text: str
    level: int | None = None
    table: Table | None = None
    inline: bool = False
    href: str | None = None
    image: ImageSource | None = None
