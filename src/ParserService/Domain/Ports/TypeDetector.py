from typing import Protocol

from ParserService.Domain.Documents.Detection import Detection
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason


class TypeDetector(Protocol):
    """Finds the real type of a file from its content; the extension is only a hint."""

    def detect(self, source: SourceFile) -> Result[Detection, FailureReason]:
        """Detect the type of a file.

        Args:
            source: The file to inspect.

        Returns:
            The detected type, or ``UNSUPPORTED_TYPE`` when the content is not a
            supported format. The detector never guesses a type it cannot confirm.
        """
        ...
