from pathlib import Path

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.PptxDocumentAssembler import PptxDocumentAssembler
from ParserService.Infrastructure.Extraction.PptxReader import PptxReader


class PptxExtractor:
    """Extractor for PowerPoint files: slide titles, text, bullet lists, tables, image alt text."""

    def __init__(self, reader: PptxReader, assembler: PptxDocumentAssembler) -> None:
        self._reader = reader
        self._assembler = assembler

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Extract a PPTX file.

        Args:
            request: The file, its facts and its detection.

        Returns:
            The parsed document, or ``corrupted_file`` when the package is broken.
        """
        slides = self._reader.read(Path(request.source.location))
        if slides.is_err:
            return Result.err(slides.unwrap_err())
        return Result.ok(self._assembler.build(request, slides.unwrap()))
