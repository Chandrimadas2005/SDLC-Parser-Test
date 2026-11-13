import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from ParserService.Infrastructure.Cli.CliFormat import CliFormat
from ParserService.Infrastructure.Cli.CliOption import CliOption


@dataclass(frozen=True, slots=True)
class CliRequest:
    """One ``parser-cli parse`` call.

    ``output`` is the folder to save into, or ``None`` to print to the terminal
    in ``output_format``. ``summary`` is true only when ``--summary`` was given.
    """

    source: Path
    output: Path | None
    output_format: CliFormat
    summary: bool

    @classmethod
    def from_arguments(cls, options: argparse.Namespace) -> Self:
        """Build the request from parsed command-line arguments.

        Args:
            options: What ``CliArgumentParser`` parsed.

        Returns:
            The request.
        """
        output = getattr(options, CliOption.OUTPUT)
        return cls(
            source=Path(getattr(options, CliOption.FILE)),
            output=None if output is None else Path(output),
            output_format=CliFormat(getattr(options, CliOption.FORMAT)),
            summary=bool(getattr(options, CliOption.SUMMARY)),
        )
