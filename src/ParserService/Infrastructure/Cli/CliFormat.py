from enum import StrEnum


class CliFormat(StrEnum):
    """The form a result is printed in when ``parser-cli`` prints to the terminal."""

    JSON = "json"
    MARKDOWN = "markdown"
