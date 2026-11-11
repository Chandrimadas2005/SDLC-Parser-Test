"""Content-based file type detection (python-magic, charset-normalizer)."""

from ParserService.Infrastructure.Detection.FileExtension import FileExtension
from ParserService.Infrastructure.Detection.FileSample import FileSample
from ParserService.Infrastructure.Detection.MagicTypeDetector import MagicTypeDetector
from ParserService.Infrastructure.Detection.MimeType import MimeType
from ParserService.Infrastructure.Detection.TextEncodingDetector import TextEncodingDetector
from ParserService.Infrastructure.Detection.ZipContentInspector import ZipContentInspector

__all__ = [
    "FileExtension",
    "FileSample",
    "MagicTypeDetector",
    "MimeType",
    "TextEncodingDetector",
    "ZipContentInspector",
]
