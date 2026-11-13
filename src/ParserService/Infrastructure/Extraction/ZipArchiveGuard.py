import zipfile
import zlib
from pathlib import Path
from typing import Final

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Config.Limits import Limits


class ZipArchiveGuard:
    """Checks a ZIP-based file against the archive limits before anything is decompressed.

    Only the archive's table of contents is read. Too many entries, or a declared
    expanded size above ``PARSER_ARCHIVE_MAX_EXPANDED_BYTES``, fail with
    ``limit_exceeded`` (brief, 2.5: archive attacks); a file that is not a readable
    ZIP fails with ``corrupted_file``. Python's ``zipfile`` never inflates an entry
    beyond its declared size, so the check also bounds what extraction can produce.

    Format-neutral on purpose: it is meant to be replaced by, or merged into, the
    shared archive-check class once that lands on the default branch.
    """

    ERRORS: Final = (OSError, EOFError, zipfile.BadZipFile, zlib.error)

    def __init__(self, limits: Limits) -> None:
        self._limits = limits

    def check(self, path: Path) -> Result[Path, FailureReason]:
        """Check an archive.

        Args:
            path: The ZIP-based file.

        Returns:
            The same path, or why the archive must not be opened.
        """
        listed = self._entries(path)
        if listed.is_err:
            return Result.err(listed.unwrap_err())
        entries = listed.unwrap()
        expanded = sum(entry.file_size for entry in entries)
        too_many = len(entries) > self._limits.archive_max_files
        if too_many or expanded > self._limits.archive_max_expanded_bytes:
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        return Result.ok(path)

    def _entries(self, path: Path) -> Result[list[zipfile.ZipInfo], FailureReason]:
        try:
            with zipfile.ZipFile(path) as archive:
                return Result.ok(archive.infolist())
        except self.ERRORS:
            return Result.err(FailureReason.CORRUPTED_FILE)
