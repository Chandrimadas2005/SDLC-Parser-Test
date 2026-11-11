from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.PlainTextBlockSplitter import PlainTextBlockSplitter
from ParserService.Infrastructure.Extraction.TextDocumentBuilder import TextDocumentBuilder
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader


class PlainTextExtractor:
    """Extractor for ``.txt`` files: one paragraph element per block of lines.

    Paragraph text is kept exactly as written, including its line breaks.
    """

    def __init__(
        self, reader: TextFileReader, splitter: PlainTextBlockSplitter, builder: TextDocumentBuilder
    ) -> None:
        self._reader = reader
        self._splitter = splitter
        self._builder = builder

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract the paragraphs of a plain text file.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed document. Plain text always yields a result, even when empty.
        """
        text = self._reader.read(request)
        return Result.ok(self._builder.build(request, self._splitter.blocks(text)))
