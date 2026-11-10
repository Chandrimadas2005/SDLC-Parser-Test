from dataclasses import dataclass

from ParserService.Domain.Jobs.ParserVersion import ParserVersion


@dataclass(frozen=True, slots=True)
class SubmitPolicy:
    """Settings that govern a submission: the parser version and the size pre-check."""

    parser_version: ParserVersion
    max_file_size_bytes: int

    def __post_init__(self) -> None:
        if self.max_file_size_bytes <= 0:
            message = "max file size must be positive"
            raise ValueError(message)
