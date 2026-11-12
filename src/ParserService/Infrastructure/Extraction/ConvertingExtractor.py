import dataclasses
import tempfile
from pathlib import Path

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Ports.Extractor import Extractor
from ParserService.Infrastructure.Extraction.LibreOfficeConverter import LibreOfficeConverter


class ConvertingExtractor:
    """Extractor for legacy formats: convert with LibreOffice, then reuse a modern extractor.

    DOC, RTF and ODT go through the DOCX extractor; ODS goes through the XLSX extractor.
    The result keeps the original file's facts (name, real type, size, hash), so the
    conversion is invisible to the caller apart from the locators, which point into
    the converted document's structure.
    """

    def __init__(
        self, converter: LibreOfficeConverter, target: DetectedType, inner: Extractor
    ) -> None:
        self._converter = converter
        self._target = target
        self._inner = inner

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Convert the file, then extract the converted copy.

        Args:
            request: The original file, its facts and its detection.

        Returns:
            The parsed document, or ``corrupted_file`` when the conversion fails.
        """
        with tempfile.TemporaryDirectory(prefix="convert-") as folder:
            source = Path(request.source.location)
            converted = self._converter.convert(source, self._target, Path(folder))
            if converted.is_err:
                return Result.err(converted.unwrap_err())
            copy = SourceFile(str(converted.unwrap()), request.source.file_name)
            return self._inner.extract(dataclasses.replace(request, source=copy))
