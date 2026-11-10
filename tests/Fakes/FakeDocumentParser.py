from ParserService.Domain.Documents import ParseOutcome
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import ArtifactPointer, FailureReason, FileName


class FakeDocumentParser:
    """DocumentParser that returns a preset result and records what it was asked."""

    def __init__(self, result: Result[ParseOutcome, FailureReason]) -> None:
        self.result = result
        self.requests: list[tuple[ArtifactPointer, FileName]] = []

    def parse(
        self, file_pointer: ArtifactPointer, file_name: FileName
    ) -> Result[ParseOutcome, FailureReason]:
        """Record the request and return the preset result."""
        self.requests.append((file_pointer, file_name))
        return self.result
