from collections.abc import Mapping
from dataclasses import dataclass

from ParserService.Infrastructure.Extraction.EmbeddedFile import EmbeddedFile
from ParserService.Infrastructure.Extraction.MailHeader import MailHeader


@dataclass(frozen=True, slots=True)
class MailContent:
    """What was read from an e-mail: headers, plain and HTML body, and attachments."""

    headers: Mapping[MailHeader, str]
    text: str | None
    html: str | None
    attachments: tuple[EmbeddedFile, ...]
