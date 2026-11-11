from typing import Protocol

from ParserService.Domain.Documents.ParseOutcome import ParseOutcome
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName


class DocumentParser(Protocol):
    """Parses a stored file, isolated from the caller (brief, section 2.5).

    A crash, hang or memory blow-up inside the parse becomes a failure reason; it
    never takes the caller down with it.
    """

    def parse(
        self, file_pointer: ArtifactPointer, file_name: FileName
    ) -> Result[ParseOutcome, FailureReason]:
        """Parse one stored file.

        Args:
            file_pointer: Where the original file is stored.
            file_name: The caller's file name, a hint for type detection.

        Returns:
            The outcome to store, or why the file could not be parsed.
        """
        ...
