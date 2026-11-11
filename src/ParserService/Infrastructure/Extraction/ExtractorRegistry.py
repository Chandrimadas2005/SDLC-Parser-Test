from collections.abc import Mapping
from typing import Self

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Ports.Extractor import Extractor
from ParserService.Infrastructure.Extraction.MarkdownBlockReader import MarkdownBlockReader
from ParserService.Infrastructure.Extraction.MarkdownExtractor import MarkdownExtractor
from ParserService.Infrastructure.Extraction.PdfDocumentAssembler import PdfDocumentAssembler
from ParserService.Infrastructure.Extraction.PdfExtractor import PdfExtractor
from ParserService.Infrastructure.Extraction.PdfReader import PdfReader
from ParserService.Infrastructure.Extraction.PlainTextBlockSplitter import PlainTextBlockSplitter
from ParserService.Infrastructure.Extraction.PlainTextExtractor import PlainTextExtractor
from ParserService.Infrastructure.Extraction.TextDocumentBuilder import TextDocumentBuilder
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader


class ExtractorRegistry:
    """Finds the extractor for a detected type: one extractor per format.

    Adding a format means registering one more extractor here; no other extractor
    changes (brief, section 2.1).
    """

    def __init__(self, extractors: Mapping[DetectedType, Extractor]) -> None:
        self._extractors = dict(extractors)

    @classmethod
    def default(cls) -> Self:
        """Build the registry with every extractor that exists today.

        Returns:
            A registry for PDF, plain text and Markdown.
        """
        reader, builder = TextFileReader(), TextDocumentBuilder()
        splitter = PlainTextBlockSplitter()
        pdf = PdfExtractor(PdfReader(), PdfDocumentAssembler(splitter))
        return cls(
            {
                DetectedType.PDF: pdf,
                DetectedType.TXT: PlainTextExtractor(reader, splitter, builder),
                DetectedType.MD: MarkdownExtractor(reader, MarkdownBlockReader(), builder),
            }
        )

    @property
    def supported_types(self) -> tuple[DetectedType, ...]:
        """The types that have an extractor, in the brief's priority order."""
        return tuple(kind for kind in DetectedType if kind in self._extractors)

    def for_type(self, detected: DetectedType) -> Result[Extractor, FailureReason]:
        """Find the extractor for a type.

        Args:
            detected: The detected file type.

        Returns:
            The extractor, or ``UNSUPPORTED_TYPE`` when the format has none yet.
        """
        extractor = self._extractors.get(detected)
        if extractor is None:
            return Result.err(FailureReason.UNSUPPORTED_TYPE)
        return Result.ok(extractor)
