from enum import IntEnum
from typing import Self

from ParserService.Domain.Documents.DocumentStatus import DocumentStatus


class CliExitCode(IntEnum):
    """Exit codes of ``parser-cli``.

    ``FAILED`` covers every failure: parsing failed, the input is missing or too
    large, the output could not be written, or the arguments were wrong.
    """

    SUCCEEDED = 0
    FAILED = 1
    PARTIAL = 2

    @classmethod
    def of(cls, status: DocumentStatus) -> Self:
        """The exit code for a parse status.

        Args:
            status: The parse result's status.

        Returns:
            The matching exit code.
        """
        return cls[status.name]
