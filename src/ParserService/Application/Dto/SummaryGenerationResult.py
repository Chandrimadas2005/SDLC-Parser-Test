from dataclasses import dataclass

from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.Summary import Summary


@dataclass(frozen=True, slots=True)
class SummaryGenerationResult:
    """The parse result after the optional summary step, and the summary if one was made.

    ``document`` is the parse result unchanged, except for one ``summary_unavailable``
    warning when a summary was asked for and could not be made.
    """

    document: ParsedDocument
    summary: Summary | None
