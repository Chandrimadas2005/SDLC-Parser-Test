from collections.abc import Callable, Mapping
from typing import Final

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Infrastructure.Extraction.Html.HtmlAttribute import HtmlAttribute
from ParserService.Infrastructure.Extraction.Html.HtmlBlock import HtmlBlock
from ParserService.Infrastructure.Extraction.Html.HtmlBlockCollector import HtmlBlockCollector
from ParserService.Infrastructure.Extraction.Html.HtmlBlockStyle import HtmlBlockStyle
from ParserService.Infrastructure.Extraction.Html.HtmlImageReader import HtmlImageReader
from ParserService.Infrastructure.Extraction.Html.HtmlReading import HtmlReading
from ParserService.Infrastructure.Extraction.Html.HtmlRole import HtmlRole
from ParserService.Infrastructure.Extraction.Html.HtmlStep import HtmlStep
from ParserService.Infrastructure.Extraction.Html.HtmlTableReader import HtmlTableReader
from ParserService.Infrastructure.Extraction.Html.HtmlTag import HtmlTag
from ParserService.Infrastructure.Extraction.Html.HtmlWalk import HtmlWalk

type Handler = Callable[[Tag, HtmlBlockStyle, HtmlWalk], None]


class HtmlBlockReader:
    """Walks an HTML tree in reading order and turns it into blocks.

    Block elements (headings, paragraphs, list items, divisions and the like) end
    the text before them and start a new block; everything inside them is collected
    as that block's text, so text in a ``div`` or ``span`` is never lost. Tables are
    read as data. Links and images become their own elements inside the text that
    holds them. Scripts, frames, embedded objects and media are never run or
    entered: each one is recorded as skipped. Styles, templates, comments and head
    metadata are not content and are passed over. The walk is iterative (see
    ``HtmlWalk``), so no nesting depth can crash it.
    """

    HEADING_LEVELS: Final[Mapping[str, int]] = {
        HtmlTag.H1: 1,
        HtmlTag.H2: 2,
        HtmlTag.H3: 3,
        HtmlTag.H4: 4,
        HtmlTag.H5: 5,
        HtmlTag.H6: 6,
    }
    BLOCK_TAGS: Final = frozenset(
        {
            *HEADING_LEVELS,
            *(HtmlTag.HTML, HtmlTag.HEAD, HtmlTag.BODY, HtmlTag.P, HtmlTag.LI, HtmlTag.UL),
            *(HtmlTag.OL, HtmlTag.DL, HtmlTag.DT, HtmlTag.DD, HtmlTag.PRE, HtmlTag.BLOCKQUOTE),
            *(HtmlTag.DIV, HtmlTag.SECTION, HtmlTag.ARTICLE, HtmlTag.MAIN, HtmlTag.HEADER),
            *(HtmlTag.FOOTER, HtmlTag.NAV, HtmlTag.ASIDE, HtmlTag.FIGURE, HtmlTag.FIGCAPTION),
            *(HtmlTag.FORM, HtmlTag.FIELDSET, HtmlTag.LEGEND, HtmlTag.ADDRESS, HtmlTag.DETAILS),
            *(HtmlTag.SUMMARY, HtmlTag.NOSCRIPT, HtmlTag.HR, HtmlTag.CAPTION),
        }
    )
    SKIPPED_TAGS: Final = frozenset(
        {
            *(HtmlTag.SCRIPT, HtmlTag.IFRAME, HtmlTag.FRAME, HtmlTag.FRAMESET, HtmlTag.OBJECT),
            *(HtmlTag.EMBED, HtmlTag.APPLET, HtmlTag.SVG, HtmlTag.MATH, HtmlTag.CANVAS),
            *(HtmlTag.AUDIO, HtmlTag.VIDEO),
        }
    )
    IGNORED_TAGS: Final = frozenset(
        {HtmlTag.TITLE, HtmlTag.META, HtmlTag.LINK, HtmlTag.BASE, HtmlTag.STYLE, HtmlTag.TEMPLATE}
    )
    ROLES: Final[Mapping[str, HtmlRole]] = {
        **dict.fromkeys(BLOCK_TAGS, HtmlRole.BLOCK),
        **dict.fromkeys(SKIPPED_TAGS, HtmlRole.SKIPPED),
        **dict.fromkeys(IGNORED_TAGS, HtmlRole.IGNORED),
        HtmlTag.TABLE: HtmlRole.TABLE,
        HtmlTag.IMG: HtmlRole.IMAGE,
        HtmlTag.A: HtmlRole.LINK,
        HtmlTag.BR: HtmlRole.BREAK,
    }
    PARAGRAPH: Final = HtmlBlockStyle(ElementKind.PARAGRAPH)
    LIST_ITEM: Final = HtmlBlockStyle(ElementKind.LIST_ITEM)
    UNSAFE_SCHEMES: Final = ("javascript:", "vbscript:", "data:")
    LINE_BREAK: Final = "\n"

    def __init__(self, tables: HtmlTableReader, images: HtmlImageReader) -> None:
        self._tables = tables
        self._images = images
        self._handlers: Mapping[HtmlRole, Handler] = {
            HtmlRole.BLOCK: self._block,
            HtmlRole.INLINE: self._inline,
            HtmlRole.TABLE: self._table,
            HtmlRole.IMAGE: self._image,
            HtmlRole.LINK: self._link,
            HtmlRole.BREAK: self._break,
            HtmlRole.IGNORED: self._ignore,
            HtmlRole.SKIPPED: self._skip,
        }

    def read(self, soup: BeautifulSoup) -> HtmlReading:
        """Walk a parsed HTML document.

        Args:
            soup: The parsed document.

        Returns:
            Its blocks in reading order and the elements that were skipped.
        """
        walk = HtmlWalk(HtmlBlockCollector())
        walk.flush_after(self.PARAGRAPH)
        walk.enter(soup, self.PARAGRAPH)
        step = walk.next()
        while step is not None:
            self._step(step, walk)
            step = walk.next()
        return walk.collector.reading()

    def _step(self, step: HtmlStep, walk: HtmlWalk) -> None:
        if step.node is None:
            walk.collector.flush(step.style)
        elif isinstance(step.node, Tag):
            role = self.ROLES.get(step.node.name, HtmlRole.INLINE)
            self._handlers[role](step.node, step.style, walk)
        elif type(step.node) is NavigableString:
            walk.collector.add_text(str(step.node))

    def _block(self, tag: Tag, style: HtmlBlockStyle, walk: HtmlWalk) -> None:
        inner = self._style(tag, style)
        walk.collector.flush(style)
        walk.flush_after(inner)
        walk.enter(tag, inner)

    def _inline(self, tag: Tag, style: HtmlBlockStyle, walk: HtmlWalk) -> None:
        walk.enter(tag, style)

    def _style(self, tag: Tag, outer: HtmlBlockStyle) -> HtmlBlockStyle:
        level = self.HEADING_LEVELS.get(tag.name)
        if level is not None:
            return HtmlBlockStyle(ElementKind.HEADING, level)
        if tag.name == HtmlTag.LI or outer.kind is ElementKind.LIST_ITEM:
            return self.LIST_ITEM
        return self.PARAGRAPH

    def _table(self, tag: Tag, style: HtmlBlockStyle, walk: HtmlWalk) -> None:
        walk.collector.flush(style)
        walk.collector.add_block(HtmlBlock(ElementKind.TABLE, "", table=self._tables.read(tag)))

    def _image(self, tag: Tag, _style: HtmlBlockStyle, walk: HtmlWalk) -> None:
        alt = HtmlAttribute.ALT.of(tag)
        image = self._images.read(tag)
        walk.collector.add_inline(HtmlBlock(ElementKind.IMAGE, alt, inline=True, image=image))

    def _link(self, tag: Tag, style: HtmlBlockStyle, walk: HtmlWalk) -> None:
        href = HtmlAttribute.HREF.of(tag)
        if href and self._is_unsafe(href):
            walk.collector.skip()
        elif href:
            text = " ".join(tag.get_text().split())
            link = HtmlBlock(ElementKind.LINK, text, inline=True, href=href)
            walk.collector.add_inline(link)
        walk.enter(tag, style)

    def _is_unsafe(self, href: str) -> bool:
        compact = "".join(char for char in href if char.isprintable() and not char.isspace())
        return compact.lower().startswith(self.UNSAFE_SCHEMES)

    def _break(self, _tag: Tag, _style: HtmlBlockStyle, walk: HtmlWalk) -> None:
        walk.collector.add_text(self.LINE_BREAK)

    def _ignore(self, _tag: Tag, _style: HtmlBlockStyle, _walk: HtmlWalk) -> None:
        return

    def _skip(self, _tag: Tag, _style: HtmlBlockStyle, walk: HtmlWalk) -> None:
        walk.collector.skip()
