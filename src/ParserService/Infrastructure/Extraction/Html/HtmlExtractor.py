import warnings
from pathlib import Path
from typing import Final

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning, XMLParsedAsHTMLWarning

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.Html.HtmlDocumentBuilder import HtmlDocumentBuilder


class HtmlExtractor:
    """Extractor for HTML files (brief, section 2.1).

    The file is parsed with BeautifulSoup on the lxml HTML parser, which repairs
    malformed markup the way browsers do and never runs scripts or loads anything.
    The character encoding comes from the document's own declaration, or is
    detected when there is none.
    """

    PARSER: Final = "lxml"
    PARSER_WARNINGS: Final = (MarkupResemblesLocatorWarning, XMLParsedAsHTMLWarning)

    def __init__(self, builder: HtmlDocumentBuilder) -> None:
        self._builder = builder

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract an HTML file.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed document, or ``corrupted_file`` when the file cannot be read.
        """
        content = self._read(Path(request.source.location))
        if content.is_err:
            return Result.err(content.unwrap_err())
        return Result.ok(self._builder.build(request, self._soup(content.unwrap())))

    @staticmethod
    def _read(path: Path) -> Result[bytes, FailureReason]:
        try:
            return Result.ok(path.read_bytes())
        except OSError:
            return Result.err(FailureReason.CORRUPTED_FILE)

    def _soup(self, content: bytes) -> BeautifulSoup:
        with warnings.catch_warnings():
            for category in self.PARSER_WARNINGS:
                warnings.simplefilter("ignore", category)
            return BeautifulSoup(content, self.PARSER)
