from dataclasses import dataclass

from ParserService.Domain.Documents.ElementKind import ElementKind


@dataclass(frozen=True, slots=True)
class HtmlBlockStyle:
    """What the text collected inside a block element becomes: its kind, and a heading level."""

    kind: ElementKind
    level: int | None = None
