import json
from typing import Final

from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.Summary import Summary
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Cli.CliFormat import CliFormat
from ParserService.Infrastructure.Output.OutputField import OutputField
from ParserService.Infrastructure.Output.ParsedDocumentJsonEncoder import (
    JsonObject,
    ParsedDocumentJsonEncoder,
)
from ParserService.Infrastructure.Output.ParsedDocumentMarkdownRenderer import (
    ParsedDocumentMarkdownRenderer,
)


class CliRenderer:
    """Turns what ``parser-cli`` produces into text, the same for the terminal and for files.

    A parse result is its JSON (schema v1) or its Markdown version. When nothing
    could be parsed, the JSON carries only the schema version, the ``failed`` status,
    the failure reason and the file name. A summary is a short Markdown section.
    """

    INDENT: Final = 2

    def __init__(
        self,
        json_encoder: ParsedDocumentJsonEncoder,
        markdown_renderer: ParsedDocumentMarkdownRenderer,
    ) -> None:
        self._json = json_encoder
        self._markdown = markdown_renderer

    def document(self, document: ParsedDocument, output_format: CliFormat) -> str:
        """Render a parse result.

        Args:
            document: The parse result.
            output_format: JSON or Markdown.

        Returns:
            The text, ending with a newline.
        """
        if output_format is CliFormat.JSON:
            return self._json.to_json(document)
        return self._markdown.render(self._json.to_json(document).encode())

    def failure(self, file_name: FileName, reason: FailureReason, output_format: CliFormat) -> str:
        """Render the result of a parse that produced nothing.

        Args:
            file_name: The input's file name.
            reason: Why nothing could be parsed.
            output_format: JSON or Markdown.

        Returns:
            The text, ending with a newline.
        """
        if output_format is CliFormat.MARKDOWN:
            status = f"- Status: **{DocumentStatus.FAILED}**\n- Failure reason: `{reason}`\n"
            return f"# {file_name}\n\n{status}"
        payload: JsonObject = {
            OutputField.SCHEMA_VERSION: ParsedDocument.SCHEMA_VERSION,
            OutputField.STATUS: DocumentStatus.FAILED,
            OutputField.FAILURE_REASON: reason,
            OutputField.DOCUMENT: {OutputField.FILE_NAME: str(file_name)},
        }
        return json.dumps(payload, indent=self.INDENT) + "\n"

    @staticmethod
    def summary(file_name: FileName, summary: Summary) -> str:
        """Render a summary as a Markdown section.

        Args:
            file_name: The summarised file's name.
            summary: The summary.

        Returns:
            The text, ending with a newline.
        """
        return f"# Summary of {file_name}\n\n{summary.text}\n"
