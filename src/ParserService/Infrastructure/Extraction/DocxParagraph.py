from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocxParagraph:
    """One body paragraph: its accepted text, heading level, list flag and comment anchors."""

    text: str
    level: int | None
    is_list: bool
    comment_ids: tuple[str, ...]
