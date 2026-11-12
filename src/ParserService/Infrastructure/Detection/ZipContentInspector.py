import zipfile
from pathlib import Path
from typing import Final

from ParserService.Domain.Documents.DetectedType import DetectedType


class ZipContentInspector:
    """Tells Office and OpenDocument files apart from plain ZIP archives.

    Only the archive's table of contents and the tiny OpenDocument ``mimetype``
    entry are read. When the table of contents is damaged, the entry names in the
    first megabyte still identify an Office package. Nothing is extracted, so this is
    safe on untrusted archives.
    """

    MIMETYPE_ENTRY: Final = "mimetype"
    MIMETYPE_MAX_BYTES: Final = 128
    DAMAGED_SCAN_BYTES: Final = 1024 * 1024
    MACRO_ENTRY: Final = "xl/vbaProject.bin"
    MARKERS: Final = (
        ("word/document.xml", DetectedType.DOCX),
        ("xl/workbook.xml", DetectedType.XLSX),
        ("ppt/presentation.xml", DetectedType.PPTX),
    )
    OPEN_DOCUMENT: Final = (
        (b"application/vnd.oasis.opendocument.text", DetectedType.ODT),
        (b"application/vnd.oasis.opendocument.spreadsheet", DetectedType.ODS),
    )

    def inspect(self, path: Path) -> DetectedType | None:
        """Find what a ZIP-based file really is.

        Args:
            path: The file to inspect.

        Returns:
            The Office, OpenDocument or ZIP type, or ``None`` if it is not a ZIP.
        """
        try:
            with zipfile.ZipFile(path) as archive:
                return self._classify(archive)
        except zipfile.BadZipFile:
            return self._damaged(path)
        except OSError:
            return None

    def _damaged(self, path: Path) -> DetectedType | None:
        # The archive's table of contents is broken, but each entry's own header still
        # names it, so an Office package stays recognisable (and repairable later).
        with path.open("rb") as handle:
            head = handle.read(self.DAMAGED_SCAN_BYTES)
        office = next((kind for marker, kind in self.MARKERS if marker.encode() in head), None)
        if office is DetectedType.XLSX and self.MACRO_ENTRY.encode() in head:
            return DetectedType.XLSM
        return office

    def _classify(self, archive: zipfile.ZipFile) -> DetectedType:
        names = set(archive.namelist())
        office = next((kind for marker, kind in self.MARKERS if marker in names), None)
        if office is DetectedType.XLSX and self.MACRO_ENTRY in names:
            return DetectedType.XLSM
        if office is not None:
            return office
        return self._open_document(archive, names) or DetectedType.ZIP

    def _open_document(self, archive: zipfile.ZipFile, names: set[str]) -> DetectedType | None:
        if self.MIMETYPE_ENTRY not in names:
            return None
        with archive.open(self.MIMETYPE_ENTRY) as entry:
            declared = entry.read(self.MIMETYPE_MAX_BYTES).strip()
        return next((kind for mime, kind in self.OPEN_DOCUMENT if declared == mime), None)
