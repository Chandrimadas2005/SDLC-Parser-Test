from dataclasses import dataclass

from bs4.element import PageElement

from ParserService.Infrastructure.Extraction.Html.HtmlBlockStyle import HtmlBlockStyle


@dataclass(frozen=True, slots=True)
class HtmlStep:
    """One piece of pending work in a walk over an HTML tree.

    With a node, the step visits that node with the given style. Without one, it
    ends the block being collected, using the given style.
    """

    node: PageElement | None
    style: HtmlBlockStyle
