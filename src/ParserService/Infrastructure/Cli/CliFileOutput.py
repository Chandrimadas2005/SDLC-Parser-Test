from collections.abc import Mapping
from pathlib import Path
from typing import TextIO

from ParserService.Application.Dto.SummaryGenerationResult import SummaryGenerationResult
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Cli.CliFormat import CliFormat
from ParserService.Infrastructure.Cli.CliOutputFile import CliOutputFile
from ParserService.Infrastructure.Cli.CliRenderer import CliRenderer


class CliFileOutput:
    """Saves results into an output folder (``--output``, brief section 2.4), as UTF-8.

    A parse result becomes ``parsed_document.json`` (schema v1) and
    ``parsed_document.md``; a summary becomes ``summary.md``. A summary left over
    from an earlier run is removed, so the folder always matches the last run.
    When the summary fails, the result files are saved again with the
    ``summary_unavailable`` warning. Write errors are reported and return ``False``.
    """

    def __init__(self, folder: Path, renderer: CliRenderer, errors: TextIO) -> None:
        self._folder = folder
        self._renderer = renderer
        self._errors = errors

    def document(self, document: ParsedDocument) -> bool:
        """Save a parse result.

        Args:
            document: The parse result.

        Returns:
            Whether every file was written.
        """
        files = {
            CliOutputFile.DOCUMENT_JSON: self._renderer.document(document, CliFormat.JSON),
            CliOutputFile.DOCUMENT_MARKDOWN: self._renderer.document(document, CliFormat.MARKDOWN),
        }
        return self._write(files) and self._remove(CliOutputFile.SUMMARY)

    def summary(self, result: SummaryGenerationResult) -> bool:
        """Save the summary, or the result again with its ``summary_unavailable`` warning.

        Args:
            result: The outcome of the summary step.

        Returns:
            Whether every file was written.
        """
        if result.summary is None:
            return self.document(result.document)
        text = self._renderer.summary(result.document.facts.file_name, result.summary)
        return self._write({CliOutputFile.SUMMARY: text})

    def failure(self, file_name: FileName, reason: FailureReason) -> bool:
        """Save the result of a parse that produced nothing.

        Args:
            file_name: The input's file name.
            reason: Why nothing could be parsed.

        Returns:
            Whether every file was written.
        """
        files = {
            CliOutputFile.DOCUMENT_JSON: self._renderer.failure(file_name, reason, CliFormat.JSON),
            CliOutputFile.DOCUMENT_MARKDOWN: self._renderer.failure(
                file_name, reason, CliFormat.MARKDOWN
            ),
        }
        return self._write(files) and self._remove(CliOutputFile.SUMMARY)

    def _write(self, files: Mapping[CliOutputFile, str]) -> bool:
        try:
            self._folder.mkdir(parents=True, exist_ok=True)
            for name, text in files.items():
                (self._folder / name).write_text(text, encoding="utf-8", newline="\n")
        except OSError as error:
            self._errors.write(f"Could not write output to {self._folder}: {error.strerror}\n")
            return False
        return True

    def _remove(self, name: CliOutputFile) -> bool:
        try:
            (self._folder / name).unlink(missing_ok=True)
        except OSError as error:
            self._errors.write(f"Could not remove stale {name}: {error.strerror}\n")
            return False
        return True
