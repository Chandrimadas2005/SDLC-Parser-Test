from pathlib import Path
from typing import Protocol

from tools.CodeRules.Violation import Violation


class PackageRule(Protocol):
    """A code rule that inspects one package directory."""

    def check(self, directory: Path) -> list[Violation]:
        """Find violations of this rule in a package directory.

        Args:
            directory: Directory that holds Python files.

        Returns:
            The violations found, empty when the package complies.
        """
        ...
