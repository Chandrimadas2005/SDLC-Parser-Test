from enum import StrEnum


class CliOutputFile(StrEnum):
    """The files ``parser-cli`` writes into its output folder."""

    DOCUMENT_JSON = "parsed_document.json"
    DOCUMENT_MARKDOWN = "parsed_document.md"
    SUMMARY = "summary.md"
