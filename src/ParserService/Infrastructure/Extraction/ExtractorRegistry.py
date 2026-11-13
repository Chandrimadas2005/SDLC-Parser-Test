from collections.abc import Mapping
from typing import TYPE_CHECKING, Self

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Ports.Extractor import Extractor
from ParserService.Infrastructure.Config.Limits import Limits
from ParserService.Infrastructure.Detection.MagicTypeDetector import MagicTypeDetector
from ParserService.Infrastructure.Detection.TextEncodingDetector import TextEncodingDetector
from ParserService.Infrastructure.Detection.ZipContentInspector import ZipContentInspector
from ParserService.Infrastructure.Extraction.ConvertingExtractor import ConvertingExtractor
from ParserService.Infrastructure.Extraction.CsvExtractor import CsvExtractor
from ParserService.Infrastructure.Extraction.DocumentBundle import DocumentBundle
from ParserService.Infrastructure.Extraction.DocxDocumentAssembler import DocxDocumentAssembler
from ParserService.Infrastructure.Extraction.DocxExtractor import DocxExtractor
from ParserService.Infrastructure.Extraction.DocxReader import DocxReader
from ParserService.Infrastructure.Extraction.DocxStyleReader import DocxStyleReader
from ParserService.Infrastructure.Extraction.EmbeddedFileParser import EmbeddedFileParser
from ParserService.Infrastructure.Extraction.EmlReader import EmlReader
from ParserService.Infrastructure.Extraction.ExtractionContext import ExtractionContext
from ParserService.Infrastructure.Extraction.Html.HtmlBlockReader import HtmlBlockReader
from ParserService.Infrastructure.Extraction.Html.HtmlDocumentBuilder import HtmlDocumentBuilder
from ParserService.Infrastructure.Extraction.Html.HtmlElementPlacer import HtmlElementPlacer
from ParserService.Infrastructure.Extraction.Html.HtmlExtractor import HtmlExtractor
from ParserService.Infrastructure.Extraction.Html.HtmlImageReader import HtmlImageReader
from ParserService.Infrastructure.Extraction.Html.HtmlMetadataReader import HtmlMetadataReader
from ParserService.Infrastructure.Extraction.Html.HtmlTableReader import HtmlTableReader
from ParserService.Infrastructure.Extraction.ImageExtractor import ImageExtractor
from ParserService.Infrastructure.Extraction.LibreOfficeConverter import LibreOfficeConverter
from ParserService.Infrastructure.Extraction.MailAssembler import MailAssembler
from ParserService.Infrastructure.Extraction.MailExtractor import MailExtractor
from ParserService.Infrastructure.Extraction.MarkdownBlockReader import MarkdownBlockReader
from ParserService.Infrastructure.Extraction.MarkdownExtractor import MarkdownExtractor
from ParserService.Infrastructure.Extraction.MsgReader import MsgReader
from ParserService.Infrastructure.Extraction.Ods.OdsAttributes import OdsAttributes
from ParserService.Infrastructure.Extraction.Ods.OdsCellReader import OdsCellReader
from ParserService.Infrastructure.Extraction.Ods.OdsContentReader import OdsContentReader
from ParserService.Infrastructure.Extraction.Ods.OdsExtractor import OdsExtractor
from ParserService.Infrastructure.Extraction.Ods.OdsPropertyReader import OdsPropertyReader
from ParserService.Infrastructure.Extraction.Ods.OdsRowReader import OdsRowReader
from ParserService.Infrastructure.Extraction.Ods.OdsWorkbookReader import OdsWorkbookReader
from ParserService.Infrastructure.Extraction.PdfDocumentAssembler import PdfDocumentAssembler
from ParserService.Infrastructure.Extraction.PdfExtractor import PdfExtractor
from ParserService.Infrastructure.Extraction.PdfPageOcr import PdfPageOcr
from ParserService.Infrastructure.Extraction.PdfReader import PdfReader
from ParserService.Infrastructure.Extraction.PlainTextBlockSplitter import PlainTextBlockSplitter
from ParserService.Infrastructure.Extraction.PlainTextExtractor import PlainTextExtractor
from ParserService.Infrastructure.Extraction.PptxDocumentAssembler import PptxDocumentAssembler
from ParserService.Infrastructure.Extraction.PptxExtractor import PptxExtractor
from ParserService.Infrastructure.Extraction.PptxReader import PptxReader
from ParserService.Infrastructure.Extraction.PptxSlideReader import PptxSlideReader
from ParserService.Infrastructure.Extraction.RepairingExtractor import RepairingExtractor
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
from ParserService.Infrastructure.Extraction.TesseractOcr import TesseractOcr
from ParserService.Infrastructure.Extraction.TextDocumentBuilder import TextDocumentBuilder
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader
from ParserService.Infrastructure.Extraction.TextTableBuilder import TextTableBuilder
from ParserService.Infrastructure.Extraction.TsvExtractor import TsvExtractor
from ParserService.Infrastructure.Extraction.XlsExtractor import XlsExtractor
from ParserService.Infrastructure.Extraction.XlsxExtractor import XlsxExtractor
from ParserService.Infrastructure.Extraction.ZipArchiveExtractor import ZipArchiveExtractor
from ParserService.Infrastructure.Extraction.ZipArchiveGuard import ZipArchiveGuard
from ParserService.Infrastructure.Extraction.ZipSalvager import ZipSalvager

if TYPE_CHECKING:
    from ParserService.Infrastructure.Extraction.ParsePipeline import ParsePipeline


class ExtractorRegistry:
    """Finds the extractor for a detected type: one extractor per format.

    Adding a format means registering one more extractor here; no other extractor
    changes (brief, section 2.1).
    """

    def __init__(self, extractors: Mapping[DetectedType, Extractor]) -> None:
        self._extractors = dict(extractors)

    @classmethod
    def default(
        cls,
        max_pages: int | None = None,
        limits: Limits | None = None,
        context: ExtractionContext | None = None,
    ) -> Self:
        """Build the registry with every extractor that exists today.

        Args:
            max_pages: Page limit for paged formats (PDF), or ``None`` for no limit.
            limits: The archive limits ZIP-based formats are checked against; the
                defaults when not given.
            context: The caller's password and the archive depth, when they apply.

        Returns:
            A registry for every format implemented so far. DOC, RTF, ODT and PPT are
            included only when LibreOffice is installed (which also lets a damaged ODS
            be retried through conversion), and PNG, JPEG and TIFF only when Tesseract
            is. HTML and ODS are read natively.
        """
        context = context or ExtractionContext()
        extractors = cls._repairing(
            {
                **cls._document_extractors(max_pages, context.password),
                **cls._spreadsheet_extractors(),
            }
        )
        converted = cls._converted(extractors, LibreOfficeConverter.available())
        native = cls._native(limits or Limits(), converted.get(DetectedType.ODS))
        images = cls._images(TesseractOcr.available())
        containers = cls._containers(context.archive_depth, limits or Limits())
        return cls(extractors | converted | native | images | containers)

    @classmethod
    def _native(
        cls, limits: Limits, ods_fallback: Extractor | None
    ) -> dict[DetectedType, Extractor]:
        return {DetectedType.HTML: cls._html(), DetectedType.ODS: cls._ods(limits, ods_fallback)}

    @staticmethod
    def _html() -> HtmlExtractor:
        reader = HtmlBlockReader(HtmlTableReader(), HtmlImageReader())
        builder = HtmlDocumentBuilder(reader, HtmlElementPlacer(), HtmlMetadataReader())
        return HtmlExtractor(builder)

    @staticmethod
    def _ods(limits: Limits, fallback: Extractor | None) -> OdsExtractor:
        attributes = OdsAttributes()
        rows = OdsRowReader(OdsCellReader(attributes), attributes)
        content = OdsContentReader(rows, attributes)
        reader = OdsWorkbookReader(ZipArchiveGuard(limits), content, OdsPropertyReader())
        return OdsExtractor(reader, SpreadsheetTableBuilder(), fallback)

    @staticmethod
    def _document_extractors(
        max_pages: int | None, password: str | None
    ) -> dict[DetectedType, Extractor]:
        reader, builder = TextFileReader(), TextDocumentBuilder()
        splitter, tables = PlainTextBlockSplitter(), TextTableBuilder()
        pdf = PdfReader(max_pages, PdfPageOcr.available(), password)
        return {
            DetectedType.PDF: PdfExtractor(pdf, PdfDocumentAssembler(splitter)),
            DetectedType.DOCX: DocxExtractor(
                DocxReader(DocxStyleReader()), DocxDocumentAssembler(tables)
            ),
            DetectedType.PPTX: PptxExtractor(
                PptxReader(PptxSlideReader()), PptxDocumentAssembler(tables)
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
    def _repairing(extractors: dict[DetectedType, Extractor]) -> dict[DetectedType, Extractor]:
        office = (DetectedType.DOCX, DetectedType.PPTX, DetectedType.XLSX, DetectedType.XLSM)
        salvager = ZipSalvager()
        repaired = {kind: RepairingExtractor(extractors[kind], salvager) for kind in office}
        return extractors | repaired

    @classmethod
    def _containers(cls, depth: int, limits: Limits) -> dict[DetectedType, Extractor]:
        detector = MagicTypeDetector(TextEncodingDetector(), ZipContentInspector())
        files = EmbeddedFileParser(depth + 1, lambda: cls._pipeline(detector, depth + 1, limits))
        bundle = DocumentBundle()
        mail = MailAssembler(files, bundle)
        return {
            DetectedType.ZIP: ZipArchiveExtractor(limits, files, bundle),
            DetectedType.EML: MailExtractor(EmlReader(), mail),
            DetectedType.MSG: MailExtractor(MsgReader(), mail),
        }

    @classmethod
    def _pipeline(cls, detector: MagicTypeDetector, depth: int, limits: Limits) -> "ParsePipeline":
        # Imported here: ParsePipeline itself imports this registry.
        from ParserService.Infrastructure.Extraction.ParsePipeline import (  # noqa: PLC0415
            ParsePipeline,
        )

        return ParsePipeline(detector, cls.default(None, limits, ExtractionContext(None, depth)))

    @staticmethod
    def _images(ocr: TesseractOcr | None) -> dict[DetectedType, Extractor]:
        if ocr is None:
            return {}
        images = ImageExtractor(ocr, PlainTextBlockSplitter())
        return {DetectedType.PNG: images, DetectedType.JPEG: images, DetectedType.TIFF: images}

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
            DetectedType.PPT: DetectedType.PPTX,
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
