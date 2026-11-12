from collections.abc import Mapping
from typing import Self

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Ports.Extractor import Extractor
from ParserService.Infrastructure.Extraction.ConvertingExtractor import ConvertingExtractor
from ParserService.Infrastructure.Extraction.CsvExtractor import CsvExtractor
from ParserService.Infrastructure.Extraction.DocxDocumentAssembler import DocxDocumentAssembler
from ParserService.Infrastructure.Extraction.DocxExtractor import DocxExtractor
from ParserService.Infrastructure.Extraction.DocxReader import DocxReader
from ParserService.Infrastructure.Extraction.DocxStyleReader import DocxStyleReader
from ParserService.Infrastructure.Extraction.LibreOfficeConverter import LibreOfficeConverter
from ParserService.Infrastructure.Extraction.MarkdownBlockReader import MarkdownBlockReader
from ParserService.Infrastructure.Extraction.MarkdownExtractor import MarkdownExtractor
from ParserService.Infrastructure.Extraction.PdfDocumentAssembler import PdfDocumentAssembler
from ParserService.Infrastructure.Extraction.PdfExtractor import PdfExtractor
from ParserService.Infrastructure.Extraction.PdfReader import PdfReader
from ParserService.Infrastructure.Extraction.PlainTextBlockSplitter import PlainTextBlockSplitter
from ParserService.Infrastructure.Extraction.PlainTextExtractor import PlainTextExtractor
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
from ParserService.Infrastructure.Extraction.TextDocumentBuilder import TextDocumentBuilder
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader
from ParserService.Infrastructure.Extraction.TsvExtractor import TsvExtractor
from ParserService.Infrastructure.Extraction.XlsExtractor import XlsExtractor
from ParserService.Infrastructure.Extraction.XlsxExtractor import XlsxExtractor


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
            A registry for every format implemented so far. DOC, RTF, ODT and ODS are
            included only when LibreOffice is installed.
        """
        extractors = {**cls._document_extractors(), **cls._spreadsheet_extractors()}
        return cls(extractors | cls._converted(extractors, LibreOfficeConverter.available()))

    @staticmethod
    def _document_extractors() -> dict[DetectedType, Extractor]:
        reader, builder = TextFileReader(), TextDocumentBuilder()
        splitter = PlainTextBlockSplitter()
        return {
            DetectedType.PDF: PdfExtractor(PdfReader(), PdfDocumentAssembler(splitter)),
            DetectedType.DOCX: DocxExtractor(
                DocxReader(DocxStyleReader()), DocxDocumentAssembler()
            ),
            DetectedType.TXT: PlainTextExtractor(reader, splitter, builder),
            DetectedType.MD: MarkdownExtractor(reader, MarkdownBlockReader(), builder),
        }

    @staticmethod
    def _spreadsheet_extractors() -> dict[DetectedType, Extractor]:
        spreadsheet = SpreadsheetTableBuilder()
        xlsx = XlsxExtractor(spreadsheet)
        return {
            DetectedType.XLSX: xlsx,
            DetectedType.XLSM: xlsx,
            DetectedType.XLS: XlsExtractor(spreadsheet),
            DetectedType.CSV: CsvExtractor(spreadsheet),
            DetectedType.TSV: TsvExtractor(spreadsheet),
        }

    @staticmethod
    def _converted(
        extractors: dict[DetectedType, Extractor], converter: LibreOfficeConverter | None
    ) -> dict[DetectedType, Extractor]:
        if converter is None:
            return {}
        routes = {
            DetectedType.DOC: DetectedType.DOCX,
            DetectedType.RTF: DetectedType.DOCX,
            DetectedType.ODT: DetectedType.DOCX,
            DetectedType.ODS: DetectedType.XLSX,
        }
        return {
            legacy: ConvertingExtractor(converter, modern, extractors[modern])
            for legacy, modern in routes.items()
        }

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
