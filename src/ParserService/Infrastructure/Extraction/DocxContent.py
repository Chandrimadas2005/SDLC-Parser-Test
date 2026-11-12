from collections.abc import Mapping
from dataclasses import dataclass

from ParserService.Infrastructure.Extraction.DocxParagraph import DocxParagraph
from ParserService.Infrastructure.Extraction.DocxTable import DocxTable


@dataclass(frozen=True, slots=True)
class DocxContent:
    """What was read from a DOCX: body blocks in order, comments and tracked-change counts."""

    blocks: tuple[DocxParagraph | DocxTable, ...]
    comments: Mapping[str, str]
    insertions: int
    deletions: int
