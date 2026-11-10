from dataclasses import dataclass
from pathlib import Path

from ParserService.Infrastructure.Detection.FileExtension import FileExtension
from ParserService.Infrastructure.Detection.MimeType import MimeType


@dataclass(frozen=True, slots=True)
class FileSample:
    """The first bytes of a file, with what libmagic and the extension say about it."""

    path: Path
    head: bytes
    mime: MimeType | None
    hint: FileExtension | None
