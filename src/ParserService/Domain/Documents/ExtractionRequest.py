from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Self

from ParserService.Domain.Documents.Detection import Detection
from ParserService.Domain.Documents.DocumentFacts import DocumentFacts
from ParserService.Domain.Documents.SourceFile import SourceFile


@dataclass(frozen=True, slots=True)
class ExtractionRequest:
    """Everything an extractor needs: the file, its facts and what detection found."""

    source: SourceFile
    facts: DocumentFacts
    detection: Detection

    def __post_init__(self) -> None:
        if self.facts.detected_type is not self.detection.detected_type:
            message = "file facts and detection must agree on the detected type"
            raise ValueError(message)

    def with_properties(self, extra: Mapping[str, str]) -> Self:
        """Add file properties read by an extractor to the request's facts.

        Args:
            extra: Properties keyed by ``PropertyName``.

        Returns:
            The request with the merged properties.
        """
        return replace(self, facts=self.facts.with_properties(extra))
