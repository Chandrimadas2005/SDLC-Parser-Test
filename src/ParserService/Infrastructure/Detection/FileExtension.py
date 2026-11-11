from enum import StrEnum
from typing import Self

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Jobs.FileName import FileName


class FileExtension(StrEnum):
    """File name extensions the detector accepts as hints, and the type each suggests.

    The extension never decides the type on its own. It only chooses between types
    the content cannot tell apart, such as Markdown and plain text, and it is
    compared with the detected type to warn about a mismatch.
    """

    TXT = ".txt"
    TEXT = ".text"
    MD = ".md"
    MARKDOWN = ".markdown"
    CSV = ".csv"
    TSV = ".tsv"
    JSON = ".json"
    YAML = ".yaml"
    YML = ".yml"
    XML = ".xml"
    HTML = ".html"
    HTM = ".htm"
    PDF = ".pdf"
    DOCX = ".docx"
    DOC = ".doc"
    XLSX = ".xlsx"
    XLSM = ".xlsm"
    XLS = ".xls"
    PPTX = ".pptx"
    PPT = ".ppt"
    ODT = ".odt"
    ODS = ".ods"
    RTF = ".rtf"
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"
    TIF = ".tif"
    TIFF = ".tiff"
    EML = ".eml"
    MSG = ".msg"
    ZIP = ".zip"

    @classmethod
    def of(cls, file_name: FileName) -> Self | None:
        """Find the known extension of a file name.

        Args:
            file_name: The caller's file name.

        Returns:
            The extension, or ``None`` when it is missing or unknown.
        """
        return next((member for member in cls if member.value == file_name.extension), None)

    @property
    def hinted_type(self) -> DetectedType:
        """The type this extension suggests."""
        aliases = {
            FileExtension.TEXT: DetectedType.TXT,
            FileExtension.MARKDOWN: DetectedType.MD,
            FileExtension.YML: DetectedType.YAML,
            FileExtension.HTM: DetectedType.HTML,
            FileExtension.JPG: DetectedType.JPEG,
            FileExtension.TIF: DetectedType.TIFF,
        }
        alias = aliases.get(self)
        return alias if alias is not None else DetectedType(self.value.removeprefix("."))
