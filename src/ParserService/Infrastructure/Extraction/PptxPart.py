from enum import StrEnum


class PptxPart(StrEnum):
    """Parts and attribute names of a PPTX package the reader opens."""

    PRESENTATION = "ppt/presentation.xml"
    RELATIONSHIPS = "ppt/_rels/presentation.xml.rels"
    FOLDER = "ppt"
    ID = "Id"
    TARGET = "Target"
    TYPE = "type"
    DESCRIPTION = "descr"
    FIRST_ROW = "firstRow"
    ENABLED = "1"
