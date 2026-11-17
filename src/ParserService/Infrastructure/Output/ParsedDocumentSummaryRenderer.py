import json
from collections.abc import Mapping, Sequence
from typing import Final, cast

from ParserService.Infrastructure.Output.OutputField import OutputField

_TEXT_KINDS: Final = frozenset({"paragraph", "list_item"})


class ParsedDocumentSummaryRenderer:
    """Builds a short, deterministic summary of the stored ParsedDocument JSON.

    It reads only the JSON result (the same artifact ``/result`` and ``/result.md``
    use), so it works for every format without calling any outside service, the way
    the CLI's ExtractiveSummaryGenerator does for a live parse (brief, section 2.2).
    """

    MAX_OUTLINE_ENTRIES: Final = 8
    MAX_OPENING_CHARACTERS: Final = 400
    ELLIPSIS: Final = "..."

    def render(self, content: bytes) -> str:
        """Summarise a stored result.

        Args:
            content: The JSON result artifact, as stored by the worker.

        Returns:
            A short plain-text summary.
        """
        document = cast("dict[str, object]", json.loads(content))
        parts = [
            self._overview(document),
            self._outline(document),
            self._counts(document),
            self._opening(document),
            self._warnings(document),
        ]
        return "\n".join(part for part in parts if part)

    def _overview(self, document: Mapping[str, object]) -> str:
        facts = self._mapping(document.get(OutputField.DOCUMENT))
        kinds = self._element_kinds(document)
        listed = ", ".join(f"{count} {kind}" for kind, count in kinds.items())
        total = sum(int(cast("str | int", count)) for count in kinds.values())
        contents = f"{total} elements ({listed})" if kinds else "no elements"
        name = facts.get(OutputField.FILE_NAME, "unknown")
        kind = str(facts.get(OutputField.DETECTED_TYPE, "")).upper()
        size = facts.get(OutputField.SIZE_BYTES, 0)
        status = document.get(OutputField.STATUS, "unknown")
        return f"{name} ({kind}, {size} bytes) parsed as {status} with {contents}."

    def _element_kinds(self, document: Mapping[str, object]) -> Mapping[str, object]:
        metrics = self._mapping(document.get(OutputField.METRICS))
        return self._mapping(metrics.get(OutputField.ELEMENTS_BY_KIND))

    def _outline(self, document: Mapping[str, object]) -> str:
        entries = self._sequence(document.get(OutputField.OUTLINE))
        names = [str(self._mapping(entry).get(OutputField.NAME, "")) for entry in entries]
        if not names:
            return ""
        shown = names[: self.MAX_OUTLINE_ENTRIES]
        more = len(names) - len(shown)
        suffix = f" (and {more} more)" if more else ""
        return f"Outline: {'; '.join(shown)}{suffix}."

    def _counts(self, document: Mapping[str, object]) -> str:
        metrics = self._mapping(document.get(OutputField.METRICS))
        listed = [
            f"{name} {value}"
            for name, value in metrics.items()
            if name != OutputField.ELEMENTS_BY_KIND and value
        ]
        return f"Counts: {', '.join(listed)}." if listed else ""

    def _opening(self, document: Mapping[str, object]) -> str:
        opening = self._shortened(" ".join(self._texts(document)))
        return f"Opening text: {opening}" if opening else ""

    def _texts(self, document: Mapping[str, object]) -> Sequence[str]:
        found = []
        for element in self._sequence(document.get(OutputField.ELEMENTS)):
            item = self._mapping(element)
            text = item.get(OutputField.TEXT)
            if item.get(OutputField.KIND) in _TEXT_KINDS and text:
                found.append(str(text))
        return found

    def _shortened(self, text: str) -> str:
        if len(text) <= self.MAX_OPENING_CHARACTERS:
            return text
        cut = text[: self.MAX_OPENING_CHARACTERS].rsplit(" ", 1)[0]
        return cut + self.ELLIPSIS

    def _warnings(self, document: Mapping[str, object]) -> str:
        warnings = self._sequence(document.get(OutputField.WARNINGS))
        codes = [str(self._mapping(warning).get(OutputField.CODE, "")) for warning in warnings]
        return f"Warnings: {', '.join(self._tally(codes))}." if codes else ""

    @staticmethod
    def _tally(codes: Sequence[str]) -> list[str]:
        counted: dict[str, int] = {}
        for code in codes:
            counted[code] = counted.get(code, 0) + 1
        return [f"{code} x{count}" if count > 1 else code for code, count in counted.items()]

    def _mapping(self, value: object) -> Mapping[str, object]:
        return cast("dict[str, object]", value) if isinstance(value, dict) else {}

    def _sequence(self, value: object) -> Sequence[object]:
        return cast("list[object]", value) if isinstance(value, list) else []
