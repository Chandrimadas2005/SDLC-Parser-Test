from ParserService.Domain.Documents import ExtractionRequest, ParsedDocument
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason


class FakeExtractor:
    """Extractor that returns a preset result for any file."""

    def __init__(self, result: Result[ParsedDocument, FailureReason]) -> None:
        self._result = result

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Return the preset result."""
        del request
        return self._result
