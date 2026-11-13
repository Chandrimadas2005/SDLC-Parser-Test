import json
from typing import Final, cast

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.StructuredDataBuilder import StructuredDataBuilder
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader


class JsonExtractor:
    """Extracts JSON objects into headings, paragraphs and object-array tables."""

    NON_STANDARD_CONSTANT: Final = "Non-standard JSON constant"

    def __init__(self, reader: TextFileReader, builder: StructuredDataBuilder) -> None:
        self._reader = reader
        self._builder = builder

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Parse JSON safely and build source-located elements."""
        source = self._reader.read(request)
        if self._builder.is_empty(source):
            return self._builder.empty(request, source)
        try:
            values = cast("object", json.loads(source, parse_constant=self._reject_constant))
        except RecursionError:
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        except (ValueError, UnicodeError):
            return Result.err(FailureReason.CORRUPTED_FILE)
        return self._builder.result(request, source, values)

    @classmethod
    def _reject_constant(cls, token: str) -> object:
        raise ValueError(cls.NON_STANDARD_CONSTANT, token)
