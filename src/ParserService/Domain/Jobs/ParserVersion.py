from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParserVersion:
    """Version of the parser that produced, or will produce, a result."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            message = "parser version must not be blank"
            raise ValueError(message)

    def __str__(self) -> str:
        return self.value
