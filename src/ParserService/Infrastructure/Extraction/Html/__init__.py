"""HTML extractor: semantic content of HTML files, without running any of it."""

from ParserService.Infrastructure.Extraction.Html.HtmlAnchor import HtmlAnchor
from ParserService.Infrastructure.Extraction.Html.HtmlAttribute import HtmlAttribute
from ParserService.Infrastructure.Extraction.Html.HtmlBlock import HtmlBlock
from ParserService.Infrastructure.Extraction.Html.HtmlBlockCollector import HtmlBlockCollector
from ParserService.Infrastructure.Extraction.Html.HtmlBlockReader import HtmlBlockReader
from ParserService.Infrastructure.Extraction.Html.HtmlBlockStyle import HtmlBlockStyle
from ParserService.Infrastructure.Extraction.Html.HtmlDocumentBuilder import HtmlDocumentBuilder
from ParserService.Infrastructure.Extraction.Html.HtmlElementPlacer import HtmlElementPlacer
from ParserService.Infrastructure.Extraction.Html.HtmlExtractor import HtmlExtractor
from ParserService.Infrastructure.Extraction.Html.HtmlImageReader import HtmlImageReader
from ParserService.Infrastructure.Extraction.Html.HtmlMetadataReader import HtmlMetadataReader
from ParserService.Infrastructure.Extraction.Html.HtmlProperty import HtmlProperty
from ParserService.Infrastructure.Extraction.Html.HtmlReading import HtmlReading
from ParserService.Infrastructure.Extraction.Html.HtmlRole import HtmlRole
from ParserService.Infrastructure.Extraction.Html.HtmlStep import HtmlStep
from ParserService.Infrastructure.Extraction.Html.HtmlTableReader import HtmlTableReader
from ParserService.Infrastructure.Extraction.Html.HtmlTag import HtmlTag
from ParserService.Infrastructure.Extraction.Html.HtmlWalk import HtmlWalk

__all__ = [
    "HtmlAnchor",
    "HtmlAttribute",
    "HtmlBlock",
    "HtmlBlockCollector",
    "HtmlBlockReader",
    "HtmlBlockStyle",
    "HtmlDocumentBuilder",
    "HtmlElementPlacer",
    "HtmlExtractor",
    "HtmlImageReader",
    "HtmlMetadataReader",
    "HtmlProperty",
    "HtmlReading",
    "HtmlRole",
    "HtmlStep",
    "HtmlTableReader",
    "HtmlTag",
    "HtmlWalk",
]
