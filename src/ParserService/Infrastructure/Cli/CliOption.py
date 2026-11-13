from enum import StrEnum


class CliOption(StrEnum):
    """The names of ``parser-cli``'s command and arguments."""

    COMMAND = "command"
    PARSE = "parse"
    FILE = "file"
    OUTPUT = "output"
    FORMAT = "format"
    SUMMARY = "summary"

    @property
    def flag(self) -> str:
        """The option as typed on the command line, such as ``--output``."""
        return f"--{self.value}"
