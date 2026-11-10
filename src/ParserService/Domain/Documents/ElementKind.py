from enum import StrEnum


class ElementKind(StrEnum):
    """What an extracted element is (brief, section 2.2, elements in reading order)."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    IMAGE = "image"
    LINK = "link"
    FOOTNOTE = "footnote"
    COMMENT = "comment"
