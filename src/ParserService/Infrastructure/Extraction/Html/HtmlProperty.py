from enum import StrEnum


class HtmlProperty(StrEnum):
    """File properties read from an HTML document's head into ``DocumentFacts.properties``."""

    TITLE = "title"
    AUTHOR = "author"
    DESCRIPTION = "description"
    KEYWORDS = "keywords"
