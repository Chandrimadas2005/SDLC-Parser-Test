from ParserService.Domain.Documents import ParsedDocument, Summary
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason


class FakeSummaryGenerator:
    """SummaryGenerator that returns a preset result, or raises a preset error."""

    def __init__(
        self,
        result: Result[Summary, FailureReason] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result or Result.ok(Summary("Synthetic summary"))
        self._error = error
        self.documents: list[ParsedDocument] = []

    def generate(self, document: ParsedDocument) -> Result[Summary, FailureReason]:
        """Record the document, then raise the preset error or return the preset result."""
        self.documents.append(document)
        if self._error is not None:
            raise self._error
        return self._result
