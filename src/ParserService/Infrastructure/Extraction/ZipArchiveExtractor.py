import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Config.Limits import Limits
from ParserService.Infrastructure.Extraction.BundleSection import BundleSection
from ParserService.Infrastructure.Extraction.DocumentBundle import DocumentBundle
from ParserService.Infrastructure.Extraction.EmbeddedFile import EmbeddedFile
from ParserService.Infrastructure.Extraction.EmbeddedFileParser import EmbeddedFileParser


class ZipArchiveExtractor:
    """Extractor for ZIP archives: every file inside is parsed like an upload (brief 2.5).

    Limits are checked from the archive's table of contents before anything is
    decompressed: number of files, total expanded size and nesting depth (archives
    inside archives); above any of them the archive fails with ``limit_exceeded``.
    Each entry is also read with a cap, so a lying size cannot exhaust memory.
    Encrypted entries are skipped with a warning. Entry names are never used as
    paths, so an entry like ``../../x`` cannot write anywhere (zip slip).
    """

    ENCRYPTED: Final = 0x1

    def __init__(self, limits: Limits, files: EmbeddedFileParser, bundle: DocumentBundle) -> None:
        self._limits = limits
        self._files = files
        self._bundle = bundle

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Parse every file in the archive.

        Args:
            request: The archive, its facts and its detection.

        Returns:
            One document with a section per file, ``limit_exceeded`` above a limit,
            or ``corrupted_file`` when the archive cannot be read.
        """
        if self._files.depth > self._limits.archive_max_depth:
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        try:
            with zipfile.ZipFile(Path(request.source.location)) as archive:
                return self._parse(request, archive)
        except (zipfile.BadZipFile, OSError):
            return Result.err(FailureReason.CORRUPTED_FILE)

    def _parse(
        self, request: ExtractionRequest, archive: zipfile.ZipFile
    ) -> Result[ParsedDocument, FailureReason]:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        expanded = sum(entry.file_size for entry in entries)
        if (
            len(entries) > self._limits.archive_max_files
            or expanded > self._limits.archive_max_expanded_bytes
        ):
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        sections = list(self._sections(archive, entries))
        if len(sections) < len(entries):
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        return Result.ok(self._bundle.build(request, sections))

    def _sections(
        self, archive: zipfile.ZipFile, entries: list[zipfile.ZipInfo]
    ) -> Iterator[BundleSection]:
        for entry in entries:
            if entry.flag_bits & self.ENCRYPTED:
                yield BundleSection(entry.filename, Result.err(FailureReason.PASSWORD_PROTECTED))
                continue
            content = self._read(archive, entry)
            if content is None:
                return
            yield BundleSection(
                entry.filename, self._files.parse(EmbeddedFile(entry.filename, content))
            )

    @staticmethod
    def _read(archive: zipfile.ZipFile, entry: zipfile.ZipInfo) -> bytes | None:
        with archive.open(entry) as stream:
            content = stream.read(entry.file_size + 1)
        return None if len(content) > entry.file_size else content
