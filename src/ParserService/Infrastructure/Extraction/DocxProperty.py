from enum import StrEnum


class DocxProperty(StrEnum):
    """File properties a DOCX result adds: how many tracked changes the document holds."""

    TRACKED_INSERTIONS = "tracked_insertions"
    TRACKED_DELETIONS = "tracked_deletions"
