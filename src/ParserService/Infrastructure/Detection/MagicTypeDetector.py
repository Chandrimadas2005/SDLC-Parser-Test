import re
from collections.abc import Mapping
from pathlib import Path
from typing import Final
from xml.etree.ElementTree import ParseError

import magic
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Documents.Detection import Detection
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Detection.FileExtension import FileExtension
from ParserService.Infrastructure.Detection.FileSample import FileSample
from ParserService.Infrastructure.Detection.MimeType import MimeType
from ParserService.Infrastructure.Detection.TextEncodingDetector import TextEncodingDetector
from ParserService.Infrastructure.Detection.ZipContentInspector import ZipContentInspector


class MagicTypeDetector:
    """TypeDetector that reads the file's content with libmagic (brief, section 2.1).

    Only the first bytes are read, plus the table of contents of ZIP-based files.
    The extension only chooses between types the content cannot tell apart (plain
    text versus Markdown, an HTML fragment that libmagic reports as plain text, or
    the legacy Office formats); when it disagrees with the
    content, the content wins and an ``extension_mismatch`` warning is added.
    """

    SAMPLE_BYTES: Final = 64 * 1024
    ZIP_SIGNATURE: Final = b"PK\x03\x04"
    HEADER_LINE: Final = re.compile(rb"^[A-Za-z][A-Za-z0-9-]*: ")
    MIME_HEADER: Final = b"MIME-Version:"
    YAML_SHAPE: Final = re.compile(rb"(?m)^[ \t]*(?:[A-Za-z_][A-Za-z0-9_.-]*:|-[ \t]+[^\r\n]+)")
    # XML without an <?xml ...?> declaration is plain text to libmagic.
    XML_SHAPE: Final = re.compile(rb"\A(?:\xef\xbb\xbf)?\s*<[A-Za-z_][\w.:-]*(?:\s[^>]*)?/?>")
    XML_END: Final = b">"
    DIRECT: Final[Mapping[MimeType, DetectedType]] = {
        MimeType.PDF: DetectedType.PDF,
        MimeType.PNG: DetectedType.PNG,
        MimeType.JPEG: DetectedType.JPEG,
        MimeType.TIFF: DetectedType.TIFF,
        MimeType.RTF: DetectedType.RTF,
        MimeType.HTML: DetectedType.HTML,
        MimeType.XML: DetectedType.XML,
        MimeType.APPLICATION_XML: DetectedType.XML,
        MimeType.JSON: DetectedType.JSON,
        MimeType.EMAIL: DetectedType.EML,
        MimeType.MS_WORD: DetectedType.DOC,
        MimeType.MS_EXCEL: DetectedType.XLS,
        MimeType.MS_POWERPOINT: DetectedType.PPT,
        MimeType.MS_OUTLOOK: DetectedType.MSG,
    }
    TEXT_MIMES: Final = frozenset(
        {MimeType.PLAIN_TEXT, MimeType.CSV, MimeType.MARKDOWN, MimeType.EMPTY, MimeType.INODE_EMPTY}
    )
    # Plain-text formats that look alike to libmagic; the extension picks among them.
    # An e-mail without a Received header is plain text to libmagic, hence EML here.
    TEXT_TYPES: Final = frozenset(
        {
            DetectedType.TXT,
            DetectedType.MD,
            DetectedType.CSV,
            DetectedType.TSV,
            DetectedType.YAML,
            DetectedType.JSON,
            DetectedType.XML,
            DetectedType.HTML,
            DetectedType.EML,
        }
    )
    OLE_TYPES: Final = frozenset(
        {DetectedType.DOC, DetectedType.XLS, DetectedType.PPT, DetectedType.MSG}
    )

    def __init__(self, encodings: TextEncodingDetector, zips: ZipContentInspector) -> None:
        self._encodings = encodings
        self._zips = zips

    def detect(self, source: SourceFile) -> Result[Detection, FailureReason]:
        """Detect the real type of a file from its content.

        Args:
            source: The file to inspect.

        Returns:
            The detection, or ``UNSUPPORTED_TYPE`` when the content is not a known format.
        """
        path = Path(source.location)
        with path.open("rb") as handle:
            head = handle.read(self.SAMPLE_BYTES)
        sample = FileSample(path, head, self._mime(head), FileExtension.of(source.file_name))
        binary = self._email(sample) or self._binary_type(sample)
        if binary is not None:
            return Result.ok(Detection(binary, None, self._mismatch(binary, sample)))
        return self._text(sample)

    @staticmethod
    def _mime(head: bytes) -> MimeType | None:
        reported = magic.from_buffer(head, mime=True)
        return next((known for known in MimeType if known.value == reported), None)

    def _binary_type(self, sample: FileSample) -> DetectedType | None:
        if sample.head.startswith(self.ZIP_SIGNATURE):
            return self._zips.inspect(sample.path)
        if sample.mime is MimeType.OLE_STORAGE:
            return self._hinted(sample, self.OLE_TYPES)
        return None if sample.mime is None else self.DIRECT.get(sample.mime)

    def _email(self, sample: FileSample) -> DetectedType | None:
        # libmagic calls an e-mail without a Received header plain text or HTML.
        first_line = sample.head.split(b"\n", 1)[0]
        looks_like_header = self.HEADER_LINE.match(first_line) is not None
        hinted = self._hinted(sample, frozenset({DetectedType.EML}))
        return hinted if looks_like_header and self.MIME_HEADER in sample.head else None

    def _text(self, sample: FileSample) -> Result[Detection, FailureReason]:
        is_text = sample.mime in self.TEXT_MIMES
        encoding = self._encodings.encoding(sample.head) if is_text else None
        if encoding is None:
            return Result.err(FailureReason.UNSUPPORTED_TYPE)
        default = DetectedType.CSV if sample.mime is MimeType.CSV else DetectedType.TXT
        detected = self._sniffed(sample, self._hinted(sample, self.TEXT_TYPES) or default)
        guessed = (ParseWarning(WarningCode.ENCODING_GUESSED),)
        extra = guessed if self._encodings.is_guess(encoding) else ()
        return Result.ok(Detection(detected, encoding, self._mismatch(detected, sample) + extra))

    def _sniffed(self, sample: FileSample, detected: DetectedType) -> DetectedType:
        if detected is not DetectedType.TXT:
            return detected
        if self._is_xml(sample.head):
            return DetectedType.XML
        return DetectedType.YAML if self.YAML_SHAPE.search(sample.head) else DetectedType.TXT

    def _is_xml(self, head: bytes) -> bool:
        if self.XML_SHAPE.match(head) is None or not head.rstrip().endswith(self.XML_END):
            return False
        # Only the start of a large file is read, so its shape decides.
        return len(head) >= self.SAMPLE_BYTES or self._parses_as_xml(head)

    @staticmethod
    def _parses_as_xml(head: bytes) -> bool:
        try:
            ElementTree.fromstring(head)
        except DefusedXmlException:
            return True  # hostile XML: the XML extractor rejects it with limit_exceeded
        except (ParseError, ValueError):
            return False
        return True

    @staticmethod
    def _hinted(sample: FileSample, allowed: frozenset[DetectedType]) -> DetectedType | None:
        if sample.hint is not None and sample.hint.hinted_type in allowed:
            return sample.hint.hinted_type
        return None

    @staticmethod
    def _mismatch(detected: DetectedType, sample: FileSample) -> tuple[ParseWarning, ...]:
        if sample.hint is None or sample.hint.hinted_type is detected:
            return ()
        return (ParseWarning(WarningCode.EXTENSION_MISMATCH),)
