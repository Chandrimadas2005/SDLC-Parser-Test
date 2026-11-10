from enum import StrEnum


class OutlineKind(StrEnum):
    """What an outline entry points at (brief, section 2.2).

    Headings for documents, sheet names for spreadsheets, slide titles for
    presentations.
    """

    HEADING = "heading"
    SHEET = "sheet"
    SLIDE = "slide"
