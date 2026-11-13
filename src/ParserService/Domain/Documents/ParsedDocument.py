from dataclasses import dataclass
from typing import ClassVar

from ParserService.Domain.Documents.DocumentFacts import DocumentFacts
from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.Element import Element
from ParserService.Domain.Documents.Metrics import Metrics
from ParserService.Domain.Documents.OutlineEntry import OutlineEntry
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Jobs.FailureReason import FailureReason


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """The result of parsing one file (brief, section 2.3).

    A failed result names its failure reason; only a failed result has one. A
    partial result carries at least one warning, which says what is missing.
    Element ids are unique. ``SCHEMA_VERSION`` matches the JSON Schema in
    ``schemas/``.
    """

    SCHEMA_VERSION: ClassVar[str] = "1.2"

    status: DocumentStatus
    facts: DocumentFacts
    elements: tuple[Element, ...]
    warnings: tuple[ParseWarning, ...]
    outline: tuple[OutlineEntry, ...]
    metrics: Metrics
    failure_reason: FailureReason | None = None

    def __post_init__(self) -> None:
        self._check_status()
        self._check_unique_ids()

    @property
    def warning_count(self) -> int:
        """How many warnings the result carries."""
        return len(self.warnings)

    def _check_status(self) -> None:
        if (self.status is DocumentStatus.FAILED) != (self.failure_reason is not None):
            message = "a failed result needs a failure reason, and only failed results have one"
            raise ValueError(message)
        if self.status is DocumentStatus.PARTIAL and not self.warnings:
            message = "a partial result must say what is missing in its warnings"
            raise ValueError(message)

    def _check_unique_ids(self) -> None:
        ids = [element.element_id for element in self.elements]
        if len(set(ids)) != len(ids):
            message = "element ids must be unique"
            raise ValueError(message)
