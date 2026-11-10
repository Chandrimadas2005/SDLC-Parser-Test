from dataclasses import dataclass

from ParserService.Domain.Jobs.FileName import FileName


@dataclass(frozen=True, slots=True)
class SourceFile:
    """A file waiting to be parsed: where its bytes are and what the caller called it.

    ``location`` is an opaque reference that the Infrastructure layer resolves, such
    as a local path inside the worker. The file name is only a hint for detection.
    """

    location: str
    file_name: FileName

    def __post_init__(self) -> None:
        if not self.location.strip():
            message = "source location must not be blank"
            raise ValueError(message)
