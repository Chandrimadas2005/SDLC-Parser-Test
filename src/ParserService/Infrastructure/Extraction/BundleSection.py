from dataclasses import dataclass

from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason


@dataclass(frozen=True, slots=True)
class BundleSection:
    """One part of a container file, such as an archive entry: its title and its result."""

    title: str
    document: Result[ParsedDocument, FailureReason]
