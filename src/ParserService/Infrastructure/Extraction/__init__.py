"""One extractor per format, the registry that picks it, and the parse pipeline."""

from ParserService.Infrastructure.Extraction.ConvertingExtractor import ConvertingExtractor
from ParserService.Infrastructure.Extraction.CsvExtractor import CsvExtractor
from ParserService.Infrastructure.Extraction.DocxContent import DocxContent
from ParserService.Infrastructure.Extraction.DocxDocumentAssembler import DocxDocumentAssembler
from ParserService.Infrastructure.Extraction.DocxExtractor import DocxExtractor
from ParserService.Infrastructure.Extraction.DocxParagraph import DocxParagraph
from ParserService.Infrastructure.Extraction.DocxParagraphReader import DocxParagraphReader
from ParserService.Infrastructure.Extraction.DocxPart import DocxPart
from ParserService.Infrastructure.Extraction.DocxProperty import DocxProperty
from ParserService.Infrastructure.Extraction.DocxReader import DocxReader
from ParserService.Infrastructure.Extraction.DocxStyleReader import DocxStyleReader
from ParserService.Infrastructure.Extraction.DocxTable import DocxTable
from ParserService.Infrastructure.Extraction.ExtractorRegistry import ExtractorRegistry
from ParserService.Infrastructure.Extraction.ImageExtractor import ImageExtractor
from ParserService.Infrastructure.Extraction.LibreOfficeConverter import LibreOfficeConverter
from ParserService.Infrastructure.Extraction.MarkdownBlockReader import MarkdownBlockReader
from ParserService.Infrastructure.Extraction.MarkdownExtractor import MarkdownExtractor
from ParserService.Infrastructure.Extraction.OcrConfidence import OcrConfidence
from ParserService.Infrastructure.Extraction.OcrText import OcrText
from ParserService.Infrastructure.Extraction.ParsePipeline import ParsePipeline
from ParserService.Infrastructure.Extraction.PdfContent import PdfContent
from ParserService.Infrastructure.Extraction.PdfDocumentAssembler import PdfDocumentAssembler
from ParserService.Infrastructure.Extraction.PdfExtractor import PdfExtractor
from ParserService.Infrastructure.Extraction.PdfPageOcr import PdfPageOcr
from ParserService.Infrastructure.Extraction.PdfPageText import PdfPageText
from ParserService.Infrastructure.Extraction.PdfReader import PdfReader
from ParserService.Infrastructure.Extraction.PlainTextBlockSplitter import PlainTextBlockSplitter
from ParserService.Infrastructure.Extraction.PlainTextExtractor import PlainTextExtractor
from ParserService.Infrastructure.Extraction.PptxDocumentAssembler import PptxDocumentAssembler
from ParserService.Infrastructure.Extraction.PptxExtractor import PptxExtractor
from ParserService.Infrastructure.Extraction.PptxPart import PptxPart
from ParserService.Infrastructure.Extraction.PptxReader import PptxReader
from ParserService.Infrastructure.Extraction.PptxSlide import PptxSlide
from ParserService.Infrastructure.Extraction.PptxSlideReader import PptxSlideReader
from ParserService.Infrastructure.Extraction.RepairingExtractor import RepairingExtractor
from ParserService.Infrastructure.Extraction.SlideBlock import SlideBlock
from ParserService.Infrastructure.Extraction.SlideTag import SlideTag
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
from ParserService.Infrastructure.Extraction.TesseractOcr import TesseractOcr
from ParserService.Infrastructure.Extraction.TextBlock import TextBlock
from ParserService.Infrastructure.Extraction.TextDocumentBuilder import TextDocumentBuilder
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader
from ParserService.Infrastructure.Extraction.TextTableBuilder import TextTableBuilder
from ParserService.Infrastructure.Extraction.TsvExtractor import TsvExtractor
from ParserService.Infrastructure.Extraction.WordTag import WordTag
from ParserService.Infrastructure.Extraction.XlsExtractor import XlsExtractor
from ParserService.Infrastructure.Extraction.XlsPropertyReader import XlsPropertyReader
from ParserService.Infrastructure.Extraction.XlsxExtractor import XlsxExtractor
from ParserService.Infrastructure.Extraction.XlsxPropertyReader import XlsxPropertyReader
from ParserService.Infrastructure.Extraction.ZipSalvager import ZipSalvager

__all__ = [
    "ConvertingExtractor",
    "CsvExtractor",
    "DocxContent",
    "DocxDocumentAssembler",
    "DocxExtractor",
    "DocxParagraph",
    "DocxParagraphReader",
    "DocxPart",
    "DocxProperty",
    "DocxReader",
    "DocxStyleReader",
    "DocxTable",
    "ExtractorRegistry",
    "ImageExtractor",
    "LibreOfficeConverter",
    "MarkdownBlockReader",
    "MarkdownExtractor",
    "OcrConfidence",
    "OcrText",
    "ParsePipeline",
    "PdfContent",
    "PdfDocumentAssembler",
    "PdfExtractor",
    "PdfPageOcr",
    "PdfPageText",
    "PdfReader",
    "PlainTextBlockSplitter",
    "PlainTextExtractor",
    "PptxDocumentAssembler",
    "PptxExtractor",
    "PptxPart",
    "PptxReader",
    "PptxSlide",
    "PptxSlideReader",
    "RepairingExtractor",
    "SlideBlock",
    "SlideTag",
    "SpreadsheetTableBuilder",
    "TesseractOcr",
    "TextBlock",
    "TextDocumentBuilder",
    "TextFileReader",
    "TextTableBuilder",
    "TsvExtractor",
    "WordTag",
    "XlsExtractor",
    "XlsPropertyReader",
    "XlsxExtractor",
    "XlsxPropertyReader",
    "ZipSalvager",
]
