from dataclasses import dataclass

from ParserService.Domain.Jobs.FileName import FileName


@dataclass(frozen=True, slots=True)
class SubmitParseJobCommand:
    """A caller's request to parse one file."""

    file_name: FileName
    content: bytes
