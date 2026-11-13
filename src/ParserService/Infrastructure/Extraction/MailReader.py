from pathlib import Path
from typing import Protocol

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.MailContent import MailContent


class MailReader(Protocol):
    """Reads one e-mail format (EML or MSG) into headers, bodies and attachments."""

    def read(self, path: Path) -> Result[MailContent, FailureReason]:
        """Read an e-mail file.

        Args:
            path: The file.

        Returns:
            Its content, or ``corrupted_file`` when it cannot be read.
        """
