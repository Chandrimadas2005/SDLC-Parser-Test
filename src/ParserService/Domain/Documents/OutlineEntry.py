from dataclasses import dataclass

from ParserService.Domain.Documents.Locator import Locator
from ParserService.Domain.Documents.OutlineKind import OutlineKind


@dataclass(frozen=True, slots=True)
class OutlineEntry:
    """One line of the outline: a heading, a sheet name or a slide title.

    Heading entries carry their level; sheet and slide entries do not.
    """

    kind: OutlineKind
    name: str
    locator: Locator
    level: int | None = None
    hidden: bool | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            message = "outline entry name must not be blank"
            raise ValueError(message)
        if self.hidden is not None and self.kind is not OutlineKind.SHEET:
            message = "only sheet outline entries can carry a hidden flag"
            raise ValueError(message)
        if (self.kind is OutlineKind.HEADING) != (self.level is not None):
            message = "a heading entry needs a level, and only headings have one"
            raise ValueError(message)
