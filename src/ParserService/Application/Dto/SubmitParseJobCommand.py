from dataclasses import dataclass

from ParserService.Domain.Jobs.FileName import FileName


@dataclass(frozen=True, slots=True)
class SubmitParseJobCommand:
    """A caller's request to parse one file, with an optional password to open it."""

    file_name: FileName
    content: bytes
    password: str | None = None

    def __repr__(self) -> str:
        # Never show the file's bytes or the password in logs or tracebacks.
        return f"SubmitParseJobCommand(file_name={self.file_name!r}, password=...)"
