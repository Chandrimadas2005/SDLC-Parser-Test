from dataclasses import dataclass

from ParserService.Domain.Documents.ElementKind import ElementKind


@dataclass(frozen=True, slots=True)
class SlideBlock:
    """One item on a slide: text, list item, image (alt text) or table (cell text rows)."""

    kind: ElementKind
    text: str | None
    rows: tuple[tuple[str, ...], ...] = ()
    header_marked: bool = False
