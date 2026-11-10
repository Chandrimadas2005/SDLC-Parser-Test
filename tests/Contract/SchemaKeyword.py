from enum import StrEnum


class SchemaKeyword(StrEnum):
    """JSON Schema keywords and definition names the contract tests read."""

    DEFS = "$defs"
    ENUM = "enum"
    CONST = "const"
    PROPERTIES = "properties"
    STATUS = "status"
    DETECTED_TYPE = "detected_type"
    ELEMENT_KIND = "element_kind"
    OUTLINE_KIND = "outline_kind"
    WARNING_CODE = "warning_code"
    FAILURE_REASON = "failure_reason"
    METRIC_NAME = "metric_name"
