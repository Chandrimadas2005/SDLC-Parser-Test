from dataclasses import dataclass

from ParserService.Domain.Documents.DocumentStatus import DocumentStatus


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    """A finished parse, ready to store: its status, warning count and JSON result.

    ``content`` is the encoded ``ParsedDocument``. Only succeeded and partial parses
    produce an outcome; a failed parse returns its failure reason instead.
    """

    status: DocumentStatus
    warning_count: int
    content: bytes

    def __post_init__(self) -> None:
        if self.status is DocumentStatus.FAILED:
            message = "a failed parse has no outcome, only a failure reason"
            raise ValueError(message)
        if self.warning_count < 0:
            message = "warning count cannot be negative"
            raise ValueError(message)
