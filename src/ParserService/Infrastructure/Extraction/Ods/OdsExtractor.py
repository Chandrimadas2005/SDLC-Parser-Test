from dataclasses import replace
from pathlib import Path

from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Ports.Extractor import Extractor
from ParserService.Infrastructure.Extraction.Ods.OdsWorkbook import OdsWorkbook
from ParserService.Infrastructure.Extraction.Ods.OdsWorkbookReader import OdsWorkbookReader
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder


class OdsExtractor:
    """Extractor for OpenDocument spreadsheets (``.ods``, brief section 2.1), schema 1.1.

    Sheets are streamed natively and handed to the shared ``SpreadsheetTableBuilder``,
    so ODS gets the same header detection, column profiles, hidden-sheet flags and
    formula cells (formula plus cached value) as XLSX. Macros, scripts and embedded
    objects are never run. A sheet that cannot be read makes the result ``partial``.
    When the package cannot be read at all, the optional fallback (LibreOffice
    conversion) is tried; a repaired result carries ``file_repaired`` and is
    ``partial``.
    """

    def __init__(
        self,
        reader: OdsWorkbookReader,
        builder: SpreadsheetTableBuilder,
        fallback: Extractor | None = None,
    ) -> None:
        self._reader = reader
        self._builder = builder
        self._fallback = fallback

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract an ODS workbook.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed workbook, or why it could not be read.
        """
        read = self._reader.read(Path(request.source.location))
        if read.is_err:
            return self._repair(request, read.unwrap_err())
        return Result.ok(self._document(request, read.unwrap()))

    def _document(self, request: ExtractionRequest, workbook: OdsWorkbook) -> ParsedDocument:
        request = request.with_properties(workbook.properties)
        sheets = [sheet.as_builder_sheet() for sheet in workbook.sheets]
        built = self._builder.build(request, sheets, workbook.formulas)
        document = replace(built, warnings=(*request.detection.warnings, *built.warnings))
        return self._flagged(document, workbook.unreadable())

    def _repair(
        self, request: ExtractionRequest, reason: FailureReason
    ) -> Result[ParsedDocument, FailureReason]:
        if reason is not FailureReason.CORRUPTED_FILE or self._fallback is None:
            return Result.err(reason)
        repaired = self._fallback.extract(request)
        if repaired.is_err:
            return Result.err(FailureReason.CORRUPTED_FILE)
        warning = ParseWarning(WarningCode.FILE_REPAIRED)
        return Result.ok(self._flagged(repaired.unwrap(), (warning,)))

    @staticmethod
    def _flagged(document: ParsedDocument, warnings: tuple[ParseWarning, ...]) -> ParsedDocument:
        if not warnings:
            return document
        combined = (*document.warnings, *warnings)
        return replace(document, status=DocumentStatus.PARTIAL, warnings=combined)
