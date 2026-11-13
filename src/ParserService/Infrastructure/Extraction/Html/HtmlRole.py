from enum import StrEnum


class HtmlRole(StrEnum):
    """How the HTML extractor treats one element while it walks the tree."""

    BLOCK = "block"
    INLINE = "inline"
    TABLE = "table"
    IMAGE = "image"
    LINK = "link"
    BREAK = "break"
    IGNORED = "ignored"
    SKIPPED = "skipped"
