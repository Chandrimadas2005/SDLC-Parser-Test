from enum import StrEnum


class OdsValueType(StrEnum):
    """The ``office:value-type`` of an ODS cell: how its value is stored."""

    FLOAT = "float"
    PERCENTAGE = "percentage"
    CURRENCY = "currency"
    DATE = "date"
    TIME = "time"
    BOOLEAN = "boolean"
    STRING = "string"
