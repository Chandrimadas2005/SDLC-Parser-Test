from typing import Protocol

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason


class Extractor(Protocol):
    """Reads one file format into a ``ParsedDocument`` (brief, section 2.1).

    There is one extractor class per format, so adding a format never changes
    another extractor. Expected failures are returned, never raised.
    """

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract a file.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed document, or why nothing usable could be read.
        """
        ...
