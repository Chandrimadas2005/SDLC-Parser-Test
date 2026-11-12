from enum import StrEnum


class WordTag(StrEnum):
    """Qualified names of the WordprocessingML elements and attributes the DOCX reader uses."""

    BODY = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body"
    PARAGRAPH = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
    TABLE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl"
    ROW = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr"
    CELL = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc"
    TEXT = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
    TAB = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tab"
    BREAK = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br"
    INSERTION = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ins"
    DELETION = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}del"
    PARAGRAPH_STYLE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle"
    NUMBERING = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr"
    OUTLINE_LEVEL = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}outlineLvl"
    TABLE_HEADER = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblHeader"
    STYLE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}style"
    NAME = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}name"
    COMMENT = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}comment"
    COMMENT_START = (
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}commentRangeStart"
    )
    VAL = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
    ID = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id"
    STYLE_ID = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}styleId"
