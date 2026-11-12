from enum import StrEnum


class DocxPart(StrEnum):
    """Parts of a DOCX package the reader opens."""

    DOCUMENT = "word/document.xml"
    STYLES = "word/styles.xml"
    COMMENTS = "word/comments.xml"
