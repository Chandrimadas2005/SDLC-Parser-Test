from enum import StrEnum


class SlideTag(StrEnum):
    """Qualified names of the PresentationML and DrawingML parts the PPTX reader uses."""

    SLIDE_ID = "{http://schemas.openxmlformats.org/presentationml/2006/main}sldId"
    SHAPE = "{http://schemas.openxmlformats.org/presentationml/2006/main}sp"
    PICTURE = "{http://schemas.openxmlformats.org/presentationml/2006/main}pic"
    FRAME = "{http://schemas.openxmlformats.org/presentationml/2006/main}graphicFrame"
    PLACEHOLDER = "{http://schemas.openxmlformats.org/presentationml/2006/main}ph"
    DRAWING_PROPERTIES = "{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr"
    PARAGRAPH = "{http://schemas.openxmlformats.org/drawingml/2006/main}p"
    TEXT = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
    BREAK = "{http://schemas.openxmlformats.org/drawingml/2006/main}br"
    TABLE = "{http://schemas.openxmlformats.org/drawingml/2006/main}tbl"
    TABLE_PROPERTIES = "{http://schemas.openxmlformats.org/drawingml/2006/main}tblPr"
    ROW = "{http://schemas.openxmlformats.org/drawingml/2006/main}tr"
    CELL = "{http://schemas.openxmlformats.org/drawingml/2006/main}tc"
    RELATIONSHIP = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
    RELATIONSHIP_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
