from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PdfPageText:
    """The text layer of one PDF page, or ``None`` when the page could not be read."""

    number: int
    text: str | None
