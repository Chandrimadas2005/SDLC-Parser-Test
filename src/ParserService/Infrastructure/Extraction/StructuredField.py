from enum import StrEnum


class StructuredField(StrEnum):
    """Generated field names used when structured input has no natural key."""

    ROOT = "root"
    XML_ATTRIBUTE_PREFIX = "@"
    XML_TEXT = "#text"
