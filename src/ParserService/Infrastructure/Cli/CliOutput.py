from typing import Protocol

from ParserService.Application.Dto.SummaryGenerationResult import SummaryGenerationResult
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName


class CliOutput(Protocol):
    """Where ``parser-cli`` puts its results: the terminal, or a folder of files."""

    def document(self, document: ParsedDocument) -> bool:
        """Show or save a parse result.

        Args:
            document: The parse result.

        Returns:
            Whether it was shown or saved.
        """
        ...

    def summary(self, result: SummaryGenerationResult) -> bool:
        """Show or save the outcome of the optional summary step.

        Args:
            result: The summary, or the document flagged ``summary_unavailable``.

        Returns:
            Whether it was shown or saved.
        """
        ...

    def failure(self, file_name: FileName, reason: FailureReason) -> bool:
        """Show or save the result of a parse that produced nothing.

        Args:
            file_name: The input's file name.
            reason: Why nothing could be parsed.

        Returns:
            Whether it was shown or saved.
        """
        ...
