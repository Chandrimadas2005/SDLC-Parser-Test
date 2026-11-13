from collections.abc import Iterable
from typing import Final

from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Domain.Documents.MetricName import MetricName
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.Summary import Summary
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason


class ExtractiveSummaryGenerator:
    """SummaryGenerator that builds a summary from the parse result alone.

    It works the same for every format, because it reads only the ``ParsedDocument``:
    what the file is, its outline (headings, sheet or slide names), its counts, the
    opening text and its warnings. It calls no outside service and is deterministic,
    so the same document always gives the same summary.
    """

    MAX_OUTLINE_ENTRIES: Final = 8
    MAX_OPENING_CHARACTERS: Final = 400
    ELLIPSIS: Final = "..."
    TEXT_KINDS: Final = frozenset({ElementKind.PARAGRAPH, ElementKind.LIST_ITEM})

    def generate(self, document: ParsedDocument) -> Result[Summary, FailureReason]:
        """Summarise a parsed document.

        Args:
            document: The parse result.

        Returns:
            The summary; this generator always produces one.
        """
        parts = [
            self._overview(document),
            self._outline(document),
            self._counts(document),
            self._opening(document),
            self._warnings(document),
        ]
        return Result.ok(Summary("\n".join(part for part in parts if part)))

    def _overview(self, document: ParsedDocument) -> str:
        facts = document.facts
        kinds = document.metrics.elements_by_kind
        listed = ", ".join(f"{count} {kind}" for kind, count in kinds.items())
        contents = f"{sum(kinds.values())} elements ({listed})" if kinds else "no elements"
        return (
            f"{facts.file_name} ({facts.detected_type.upper()}, {facts.size_bytes} bytes) "
            f"parsed as {document.status} with {contents}."
        )

    def _outline(self, document: ParsedDocument) -> str:
        names = [entry.name for entry in document.outline]
        if not names:
            return ""
        shown = names[: self.MAX_OUTLINE_ENTRIES]
        more = len(names) - len(shown)
        suffix = f" (and {more} more)" if more else ""
        return f"Outline: {'; '.join(shown)}{suffix}."

    @staticmethod
    def _counts(document: ParsedDocument) -> str:
        counts = document.metrics.counts
        listed = [f"{name} {counts[name]}" for name in MetricName if counts.get(name)]
        return f"Counts: {', '.join(listed)}." if listed else ""

    def _opening(self, document: ParsedDocument) -> str:
        texts = (
            element.text
            for element in document.elements
            if element.kind in self.TEXT_KINDS and element.text
        )
        opening = self._shortened(" ".join(texts))
        return f"Opening text: {opening}" if opening else ""

    def _shortened(self, text: str) -> str:
        if len(text) <= self.MAX_OPENING_CHARACTERS:
            return text
        cut = text[: self.MAX_OPENING_CHARACTERS].rsplit(" ", 1)[0]
        return cut + self.ELLIPSIS

    def _warnings(self, document: ParsedDocument) -> str:
        codes = [str(warning.code) for warning in document.warnings]
        return f"Warnings: {', '.join(self._tally(codes))}." if codes else ""

    @staticmethod
    def _tally(codes: Iterable[str]) -> list[str]:
        counted: dict[str, int] = {}
        for code in codes:
            counted[code] = counted.get(code, 0) + 1
        return [f"{code} x{count}" if count > 1 else code for code, count in counted.items()]
