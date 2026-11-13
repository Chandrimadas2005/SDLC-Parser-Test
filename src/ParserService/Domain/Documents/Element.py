from dataclasses import dataclass
from typing import ClassVar

from ParserService.Domain.Documents.ElementId import ElementId
from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Domain.Documents.ImageSource import ImageSource
from ParserService.Domain.Documents.Locator import Locator
from ParserService.Domain.Documents.Table import Table


@dataclass(frozen=True, slots=True)
class Element:
    """One item of the document, in reading order, with where it came from.

    Headings carry a level and tables carry their data; every other kind carries
    neither. ``text`` holds the element's text, or alt text for an image. Since
    schema 1.2 a link may carry its target (``href``) and an image its source and
    declared size (``image``); no other kind carries them.
    """

    MAX_HEADING_LEVEL: ClassVar[int] = 9

    element_id: ElementId
    kind: ElementKind
    locator: Locator
    text: str | None = None
    level: int | None = None
    table: Table | None = None
    href: str | None = None
    image: ImageSource | None = None

    def __post_init__(self) -> None:
        self._check_level()
        self._check_table()
        self._check_reference()

    def _check_level(self) -> None:
        if (self.kind is ElementKind.HEADING) != (self.level is not None):
            message = "a heading needs a level, and only headings have one"
            raise ValueError(message)
        if self.level is not None and not 1 <= self.level <= self.MAX_HEADING_LEVEL:
            message = f"heading level must be 1 to {self.MAX_HEADING_LEVEL}"
            raise ValueError(message)

    def _check_table(self) -> None:
        if (self.kind is ElementKind.TABLE) != (self.table is not None):
            message = "a table element needs table data, and only tables have it"
            raise ValueError(message)

    def _check_reference(self) -> None:
        if self.href is not None and (self.kind is not ElementKind.LINK or not self.href.strip()):
            message = "only links carry an href, and it must not be blank"
            raise ValueError(message)
        if self.image is not None and self.kind is not ElementKind.IMAGE:
            message = "only images carry an image source"
            raise ValueError(message)
