from pathlib import Path

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.PdfDocumentAssembler import PdfDocumentAssembler
from ParserService.Infrastructure.Extraction.PdfReader import PdfReader


class PdfExtractor:
    """Extractor for PDF files with a text layer: text per page, with page locators.

    Bookmarks become the outline. Encrypted files fail with ``password_protected``
    and files PDFium cannot open fail with ``corrupted_file``.
    """

    def __init__(self, reader: PdfReader, assembler: PdfDocumentAssembler) -> None:
        self._reader = reader
        self._assembler = assembler

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract the text of a PDF, page by page.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed document, or why the PDF could not be opened.
        """
        content = self._reader.read(Path(request.source.location))
        if content.is_err:
            return Result.err(content.unwrap_err())
        return Result.ok(self._assembler.build(request, content.unwrap()))
