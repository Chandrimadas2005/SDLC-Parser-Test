import dataclasses
import tempfile
from pathlib import Path

from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Ports.Extractor import Extractor
from ParserService.Infrastructure.Extraction.ZipSalvager import ZipSalvager


class RepairingExtractor:
    """Wraps an Office extractor with a repair fallback for damaged packages (brief 2.5).

    When the extractor reports ``corrupted_file``, the package is rebuilt from its
    entries' own headers and extracted again. A repaired result is ``partial`` and
    carries ``file_repaired``, so the caller knows the file was not read as is.
    """

    def __init__(self, inner: Extractor, salvager: ZipSalvager) -> None:
        self._inner = inner
        self._salvager = salvager

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract the file, repairing the package first if it is damaged.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed document, or the original failure when repair is not possible.
        """
        first = self._inner.extract(request)
        if not (first.is_err and first.unwrap_err() is FailureReason.CORRUPTED_FILE):
            return first
        with tempfile.TemporaryDirectory(prefix="repair-") as folder:
            rebuilt = Path(folder) / Path(request.source.location).name
            salvaged = self._salvager.salvage(Path(request.source.location), rebuilt)
            if salvaged.is_err:
                return first
            copy = SourceFile(str(rebuilt), request.source.file_name)
            repaired = self._inner.extract(dataclasses.replace(request, source=copy))
        if repaired.is_err:
            return first
        return Result.ok(self._mark(repaired.unwrap()))

    @staticmethod
    def _mark(document: ParsedDocument) -> ParsedDocument:
        warning = ParseWarning(WarningCode.FILE_REPAIRED)
        warnings = (*document.warnings, warning)
        return dataclasses.replace(document, status=DocumentStatus.PARTIAL, warnings=warnings)
