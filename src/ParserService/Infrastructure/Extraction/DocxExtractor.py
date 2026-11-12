from pathlib import Path

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.DocxDocumentAssembler import DocxDocumentAssembler
from ParserService.Infrastructure.Extraction.DocxReader import DocxReader


class DocxExtractor:
    """Extractor for Word files: headings, lists, tables, comments and tracked changes.

    Text is read with every tracked change accepted; the number of insertions and
    deletions is recorded in the file properties.
    """

    def __init__(self, reader: DocxReader, assembler: DocxDocumentAssembler) -> None:
        self._reader = reader
        self._assembler = assembler

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract a DOCX file.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed document, or ``corrupted_file`` when the package is broken.
        """
        content = self._reader.read(Path(request.source.location))
        if content.is_err:
            return Result.err(content.unwrap_err())
        return Result.ok(self._assembler.build(request, content.unwrap()))
