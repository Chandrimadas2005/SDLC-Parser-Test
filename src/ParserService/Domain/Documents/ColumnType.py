from enum import StrEnum


class ColumnType(StrEnum):
    """A spreadsheet column's inferred value type."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    EMPTY = "empty"
    MIXED = "mixed"
