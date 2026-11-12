from dataclasses import dataclass

from ParserService.Infrastructure.Extraction.SlideBlock import SlideBlock


@dataclass(frozen=True, slots=True)
class PptxSlide:
    """One slide: its number, title, items in order, and whether it could be read."""

    number: int
    title: str | None
    blocks: tuple[SlideBlock, ...]
    readable: bool
