from typing import Protocol

from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.Summary import Summary
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason


class SummaryGenerator(Protocol):
    """Writes an optional summary of a parsed document (brief, section 2.2).

    Summaries are off by default. A generator only reads the document; it never
    changes it, and a failure to summarise never fails the parse.
    """

    def generate(self, document: ParsedDocument) -> Result[Summary, FailureReason]:
        """Summarise a parsed document.

        Args:
            document: The parse result to summarise.

        Returns:
            The summary, or why none could be written.
        """
        ...
