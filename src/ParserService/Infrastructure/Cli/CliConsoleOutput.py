from typing import TextIO

from ParserService.Application.Dto.SummaryGenerationResult import SummaryGenerationResult
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Cli.CliFormat import CliFormat
from ParserService.Infrastructure.Cli.CliRenderer import CliRenderer


class CliConsoleOutput:
    """Prints results live on standard output; nothing is saved.

    Only results go to standard output, so it can be piped (for example into
    ``jq``). A summary, when one was asked for, follows the result as a Markdown
    section.
    """

    def __init__(self, output_format: CliFormat, renderer: CliRenderer, out: TextIO) -> None:
        self._format = output_format
        self._renderer = renderer
        self._out = out

    def document(self, document: ParsedDocument) -> bool:
        """Print a parse result.

        Args:
            document: The parse result.

        Returns:
            Always ``True``.
        """
        self._out.write(self._renderer.document(document, self._format))
        return True

    def summary(self, result: SummaryGenerationResult) -> bool:
        """Print the summary after the result, when one was made.

        Args:
            result: The outcome of the summary step.

        Returns:
            Always ``True``.
        """
        if result.summary is not None:
            name = result.document.facts.file_name
            self._out.write("\n" + self._renderer.summary(name, result.summary))
        return True

    def failure(self, file_name: FileName, reason: FailureReason) -> bool:
        """Print the result of a parse that produced nothing.

        Args:
            file_name: The input's file name.
            reason: Why nothing could be parsed.

        Returns:
            Always ``True``.
        """
        self._out.write(self._renderer.failure(file_name, reason, self._format))
        return True
