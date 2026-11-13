from dataclasses import dataclass

from ParserService.Infrastructure.Extraction.Html.HtmlBlock import HtmlBlock


@dataclass(frozen=True, slots=True)
class HtmlReading:
    """What one walk over an HTML tree found.

    ``skipped`` holds, for each element that was skipped and never run (scripts,
    frames, embedded objects, unsafe links), the paragraph number it sits in or
    just before.
    """

    blocks: tuple[HtmlBlock, ...]
    skipped: tuple[int, ...]

    @property
    def paragraph_count(self) -> int:
        """How many blocks have their own paragraph number."""
        return sum(1 for block in self.blocks if not block.inline)
