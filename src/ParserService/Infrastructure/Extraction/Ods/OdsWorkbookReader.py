import zipfile
import zlib
from pathlib import Path
from typing import Final

from defusedxml import ElementTree

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.Ods.OdsContentReader import OdsContentReader
from ParserService.Infrastructure.Extraction.Ods.OdsPropertyReader import OdsPropertyReader
from ParserService.Infrastructure.Extraction.Ods.OdsWorkbook import OdsWorkbook
from ParserService.Infrastructure.Extraction.ZipArchiveGuard import ZipArchiveGuard


class OdsWorkbookReader:
    """Opens an ODS package safely and reads its sheets and properties.

    The archive limits are checked first. A package whose manifest lists encryption
    data fails with ``password_protected``. Then ``content.xml`` is streamed: when it
    breaks part-way, the sheets read so far are kept and reported as partial; when
    nothing at all could be read, or the package holds no sheet, it fails with
    ``corrupted_file``.
    """

    CONTENT: Final = "content.xml"
    MANIFEST: Final = "META-INF/manifest.xml"
    ENCRYPTION_MARKER: Final = b"encryption-data"
    STREAM_ERRORS: Final = (
        OSError,
        EOFError,
        KeyError,
        ValueError,
        zipfile.BadZipFile,
        zlib.error,
        ElementTree.ParseError,
    )

    def __init__(
        self, guard: ZipArchiveGuard, content: OdsContentReader, properties: OdsPropertyReader
    ) -> None:
        self._guard = guard
        self._content = content
        self._properties = properties

    def read(self, path: Path) -> Result[OdsWorkbook, FailureReason]:
        """Read a workbook.

        Args:
            path: The ODS file.

        Returns:
            The workbook, or why it could not be read at all.
        """
        checked = self._guard.check(path)
        if checked.is_err:
            return Result.err(checked.unwrap_err())
        if self._encrypted(path):
            return Result.err(FailureReason.PASSWORD_PROTECTED)
        workbook = OdsWorkbook()
        self._stream(path, workbook)
        if not workbook.readable:
            return Result.err(FailureReason.CORRUPTED_FILE)
        workbook.properties = self._properties.read(path)
        return Result.ok(workbook)

    def _encrypted(self, path: Path) -> bool:
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                manifest = archive.read(self.MANIFEST) if self.MANIFEST in names else b""
        except self.STREAM_ERRORS:
            return False
        return self.ENCRYPTION_MARKER in manifest

    def _stream(self, path: Path, workbook: OdsWorkbook) -> None:
        try:
            with zipfile.ZipFile(path) as archive, archive.open(self.CONTENT) as stream:
                self._content.read(stream, workbook)
        except self.STREAM_ERRORS:
            workbook.break_off()
