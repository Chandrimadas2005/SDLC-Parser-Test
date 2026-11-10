from typing import Protocol

from tools.CodeRules.SourceFile import SourceFile
from tools.CodeRules.Violation import Violation


class FileRule(Protocol):
    """A code rule that inspects one parsed source file."""

    def check(self, source: SourceFile) -> list[Violation]:
        """Find violations of this rule in a file.

        Args:
            source: Parsed file to check.

        Returns:
            The violations found, empty when the file complies.
        """
        ...
