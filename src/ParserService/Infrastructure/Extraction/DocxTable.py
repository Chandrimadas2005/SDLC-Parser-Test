from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocxTable:
    """One body table: the text of every cell, and whether row 1 is marked as a header."""

    rows: tuple[tuple[str, ...], ...]
    header_marked: bool
