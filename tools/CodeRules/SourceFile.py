import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass(frozen=True, slots=True)
class SourceFile:
    """A parsed Python source file: its path, syntax tree and raw lines."""

    path: Path
    tree: ast.Module
    lines: tuple[str, ...]

    @classmethod
    def parse(cls, path: Path, text: str) -> Self:
        """Build a source file from text already in memory.

        Args:
            path: Path the text belongs to; used for messages and file-name rules.
            text: Python source code.

        Returns:
            The parsed source file.
        """
        return cls(
            path=path, tree=ast.parse(text, filename=str(path)), lines=tuple(text.splitlines())
        )

    @classmethod
    def load(cls, path: Path) -> Self:
        """Read and parse a UTF-8 Python file from disk.

        Args:
            path: File to read.

        Returns:
            The parsed source file.
        """
        return cls.parse(path, path.read_text(encoding="utf-8"))
