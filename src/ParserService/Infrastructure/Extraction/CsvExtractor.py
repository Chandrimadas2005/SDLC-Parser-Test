import csv
from pathlib import Path

from ParserService.Domain.Documents import DetectedType, ExtractionRequest, ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder


class CsvExtractor:
    """Extract comma-separated values into a source-located table."""

    def __init__(self, builder: SpreadsheetTableBuilder) -> None:
        self._builder = builder

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Read CSV rows with the encoding selected by type detection."""
        try:
            with Path(request.source.location).open(
                encoding=request.detection.encoding or "utf-8", newline=""
            ) as handle:
                matrix = [list(row) for row in csv.reader(handle, delimiter=",")]
        except (OSError, UnicodeError, csv.Error):
            return Result.err(FailureReason.CORRUPTED_FILE)
        return Result.ok(self._builder.build(request, [(self._name(), False, matrix)], 0))

    def _name(self) -> str:
        return DetectedType.CSV.value.upper()
