import json
from collections.abc import Mapping, Sequence
from typing import cast

from ParserService.Infrastructure.Output.OutputField import OutputField


class ParsedDocumentMarkdownRenderer:
    """Render the stored ParsedDocument JSON as a readable Markdown report."""

    def render(self, content: bytes) -> str:
        """Convert a JSON result artifact into Markdown sections."""
        document = cast(dict[str, object], json.loads(content))
        facts = self._mapping(document.get(OutputField.DOCUMENT))
        lines = ["# Parsed document", "", f"**File:** {facts.get(OutputField.FILE_NAME, 'unknown')}",
                 f"**Status:** {document.get(OutputField.STATUS, 'unknown')}", ""]
        self._append_outline(lines, document.get(OutputField.OUTLINE))
        self._append_warnings(lines, document.get(OutputField.WARNINGS))
        self._append_elements(lines, document.get(OutputField.ELEMENTS))
        return "\n".join(lines).rstrip() + "\n"

    def _append_outline(self, lines: list[str], value: object) -> None:
        entries = self._sequence(value)
        lines.extend(["## Outline", ""])
        for entry in entries:
            item = self._mapping(entry)
            lines.append(f"- {item.get(OutputField.KIND, 'item')}: {item.get(OutputField.NAME, '')}")
        lines.append("")

    def _append_warnings(self, lines: list[str], value: object) -> None:
        warnings = self._sequence(value)
        lines.extend(["## Warnings", ""])
        for warning in warnings:
            item = self._mapping(warning)
            lines.append(f"- `{item.get(OutputField.CODE, 'unknown')}`")
        lines.append("")

    def _append_elements(self, lines: list[str], value: object) -> None:
        elements = self._sequence(value)
        lines.extend(["## Elements", ""])
        for element in elements:
            self._append_element(lines, self._mapping(element))

    def _append_element(self, lines: list[str], element: Mapping[str, object]) -> None:
        kind = element.get(OutputField.KIND, "element")
        lines.append(f"### {kind}")
        text = element.get(OutputField.TEXT)
        if text is not None:
            lines.extend(["", str(text)])
        table = element.get(OutputField.ROWS)
        if table is not None:
            self._append_rows(lines, self._sequence(table))
        lines.append("")

    def _append_rows(self, lines: list[str], rows: Sequence[object]) -> None:
        for row in rows:
            cells = self._mapping(self._mapping(row).get(OutputField.CELLS))
            lines.append("- " + "; ".join(f"**{key}:** {value}" for key, value in cells.items()))

    def _mapping(self, value: object) -> Mapping[str, object]:
        return cast(dict[str, object], value) if isinstance(value, dict) else {}

    def _sequence(self, value: object) -> Sequence[object]:
        return cast(list[object], value) if isinstance(value, list) else []
