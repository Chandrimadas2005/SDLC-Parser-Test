from pathlib import Path

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.MailAssembler import MailAssembler
from ParserService.Infrastructure.Extraction.MailReader import MailReader


class MailExtractor:
    """Extractor for e-mails (EML and MSG): body, attachments and headers."""

    def __init__(self, reader: MailReader, assembler: MailAssembler) -> None:
        self._reader = reader
        self._assembler = assembler

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract an e-mail.

        Args:
            request: The e-mail file, its facts and its detection.

        Returns:
            The parsed document, or ``corrupted_file`` when the file cannot be read.
        """
        mail = self._reader.read(Path(request.source.location))
        if mail.is_err:
            return Result.err(mail.unwrap_err())
        return Result.ok(self._assembler.build(request, mail.unwrap()))
