from enum import StrEnum


class DetectedType(StrEnum):
    """The real file type, detected from the content (brief, section 2.1).

    The file extension is only a hint. Every format in the brief is listed, in its
    priority order, so the output schema does not change when a format is added.
    """

    XLSX = "xlsx"
    XLSM = "xlsm"
    XLS = "xls"
    CSV = "csv"
    TSV = "tsv"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    PPTX = "pptx"
    HTML = "html"
    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"
    ODT = "odt"
    ODS = "ods"
    RTF = "rtf"
    DOC = "doc"
    PPT = "ppt"
    EML = "eml"
    MSG = "msg"
    ZIP = "zip"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
