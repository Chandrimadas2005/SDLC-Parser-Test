from dataclasses import dataclass

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
