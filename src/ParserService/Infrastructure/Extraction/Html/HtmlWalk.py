from bs4.element import Tag

from ParserService.Infrastructure.Extraction.Html.HtmlBlockCollector import HtmlBlockCollector
from ParserService.Infrastructure.Extraction.Html.HtmlBlockStyle import HtmlBlockStyle
from ParserService.Infrastructure.Extraction.Html.HtmlStep import HtmlStep


class HtmlWalk:
    """The state of one walk over an HTML tree: pending steps and what was collected.

    The walk keeps its pending steps on a stack instead of recursing, so a document
    nested thousands of levels deep cannot exhaust Python's call stack. Steps come
    off the stack in document order.
    """

    def __init__(self, collector: HtmlBlockCollector) -> None:
        self.collector = collector
        self._steps: list[HtmlStep] = []

    def enter(self, tag: Tag, style: HtmlBlockStyle) -> None:
        """Visit an element's children next, in document order.

        Args:
            tag: The element.
            style: What text found in the children becomes.
        """
        self._steps.extend(HtmlStep(child, style) for child in reversed(tag.contents))

    def flush_after(self, style: HtmlBlockStyle) -> None:
        """End the current block once the steps pushed after this one are done.

        Args:
            style: What the block's text becomes.
        """
        self._steps.append(HtmlStep(None, style))

    def next(self) -> HtmlStep | None:
        """Take the next step.

        Returns:
            The step, or ``None`` when the walk is finished.
        """
        return self._steps.pop() if self._steps else None
