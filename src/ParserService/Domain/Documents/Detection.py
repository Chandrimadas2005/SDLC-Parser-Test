from dataclasses import dataclass

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Documents.ParseWarning import ParseWarning


@dataclass(frozen=True, slots=True)
class Detection:
    """What a file really is, found from its content (brief, section 2.1).

    ``encoding`` is set for text formats only. ``warnings`` records anything that was
    guessed, such as an extension that disagrees with the content.
    """

    detected_type: DetectedType
    encoding: str | None
    warnings: tuple[ParseWarning, ...]
