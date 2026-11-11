from dataclasses import dataclass

from ParserService.Domain.Documents.ColumnType import ColumnType


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    """Summary of the values and inferred type of one spreadsheet column."""

    name: str
    guessed_type: ColumnType
    fill_rate: float
    unique_values: int
    looks_like_id: bool

    def __post_init__(self) -> None:
        if not self.name.strip():
            message = "column profile name must not be blank"
            raise ValueError(message)
        if not 0.0 <= self.fill_rate <= 1.0:
            message = "column fill rate must be between 0.0 and 1.0"
            raise ValueError(message)
        if self.unique_values < 0:
            message = "unique value count cannot be negative"
            raise ValueError(message)
