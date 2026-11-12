from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Self

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Documents.PropertyName import PropertyName
from ParserService.Domain.Jobs.FileHash import FileHash
from ParserService.Domain.Jobs.FileName import FileName


@dataclass(frozen=True, slots=True)
class DocumentFacts:
    """Facts about the file itself (brief, section 2.2, file facts).

    Page, sheet and slide counts are given only for the formats that have them.
    ``properties`` holds the file's own metadata, such as its title or author.
    """

    file_name: FileName
    detected_type: DetectedType
    size_bytes: int
    sha256: FileHash
    page_count: int | None = None
    sheet_count: int | None = None
    slide_count: int | None = None
    language: str | None = None
    properties: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.size_bytes < 0:
            message = "file size cannot be negative"
            raise ValueError(message)
        for count in (self.page_count, self.sheet_count, self.slide_count):
            if count is not None and count < 0:
                message = "page, sheet and slide counts cannot be negative"
                raise ValueError(message)

    def with_properties(self, extra: Mapping[str, str]) -> Self:
        """Add file properties; empty values are dropped, later values win.

        Args:
            extra: Properties keyed by ``PropertyName``. Values are kept as given, so a
                tab delimiter survives.

        Returns:
            The facts with the merged properties, or unchanged when nothing is added.
            A ``language`` property declared by the file also fills ``language`` when
            it is not set yet.
        """
        kept = {name: value for name, value in extra.items() if value}
        if not kept:
            return self
        language = self.language or kept.get(PropertyName.LANGUAGE)
        properties = {**(self.properties or {}), **kept}
        return replace(self, properties=properties, language=language)
