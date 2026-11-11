from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.MarkdownBlockReader import MarkdownBlockReader
from ParserService.Infrastructure.Extraction.TextDocumentBuilder import TextDocumentBuilder
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader


class MarkdownExtractor:
    """Extractor for Markdown files: headings with levels, list items and paragraphs.

    Soft line breaks inside a paragraph are joined with a space, as Markdown
    renders them.
    """

    def __init__(
        self, reader: TextFileReader, blocks: MarkdownBlockReader, builder: TextDocumentBuilder
    ) -> None:
        self._reader = reader
        self._blocks = blocks
        self._builder = builder

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract the blocks of a Markdown file.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed document, with headings in the outline.
        """
        text = self._reader.read(request)
        return Result.ok(self._builder.build(request, self._blocks.blocks(text)))
