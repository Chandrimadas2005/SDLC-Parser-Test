from dataclasses import dataclass
from pathlib import Path

from tools.CodeRules.RuleName import RuleName


@dataclass(frozen=True, slots=True)
class Violation:
    """A single breach of a code rule, located in a source file or package."""

    path: Path
    line: int
    rule: RuleName
    message: str

    def render(self) -> str:
        """Format the violation as ``path:line: CODE message``.

        Returns:
            The single-line, human-readable form of the violation.
        """
        return f"{self.path.as_posix()}:{self.line}: {self.rule} {self.message}"
