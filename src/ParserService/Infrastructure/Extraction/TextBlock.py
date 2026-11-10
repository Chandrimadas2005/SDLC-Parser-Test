from dataclasses import dataclass

from ParserService.Domain.Documents.ElementKind import ElementKind


@dataclass(frozen=True, slots=True)
class TextBlock:
    """One block found in a text file, with its character span in the decoded text.

    ``start`` is inclusive and ``end`` exclusive, so ``text[start:end]`` is the block
    as it appears in the file. ``content`` is the block's clean text, without
    Markdown markers such as ``#`` or ``-``.
    """

    kind: ElementKind
    content: str
    start: int
    end: int
    level: int | None = None
