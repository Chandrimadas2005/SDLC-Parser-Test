from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CellValue:
    """A spreadsheet cell's literal value, formula and cached calculation."""

    value: str | None = None
    formula: str | None = None
    calculated_value: str | int | float | bool | None = None
