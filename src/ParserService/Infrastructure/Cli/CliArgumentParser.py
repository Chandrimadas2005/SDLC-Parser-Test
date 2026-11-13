import argparse
import sys
from typing import NoReturn, Self

from ParserService.Infrastructure.Cli.CliExitCode import CliExitCode
from ParserService.Infrastructure.Cli.CliFormat import CliFormat
from ParserService.Infrastructure.Cli.CliOption import CliOption


class CliArgumentParser(argparse.ArgumentParser):
    """The argument parser of ``parser-cli``.

    A usage error exits with ``CliExitCode.FAILED``. argparse's own code for that
    is 2, which ``parser-cli`` reserves for a partial result.
    """

    PROGRAM = "parser-cli"

    def error(self, message: str) -> NoReturn:
        """Report a usage error and exit with the failure code.

        Args:
            message: What was wrong with the arguments.

        Raises:
            SystemExit: Always, with ``CliExitCode.FAILED``.
        """
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        raise SystemExit(CliExitCode.FAILED)

    @classmethod
    def build(cls) -> Self:
        """Build the parser with the ``parse`` command.

        Returns:
            The parser.
        """
        parser = cls(prog=cls.PROGRAM, description="Parse files without the web server.")
        commands = parser.add_subparsers(dest=CliOption.COMMAND, required=True)
        parse = commands.add_parser(
            CliOption.PARSE, help="parse one file into a ParsedDocument (JSON and Markdown)"
        )
        cls._parse_arguments(parse)
        return parser

    @staticmethod
    def _parse_arguments(parse: argparse.ArgumentParser) -> None:
        parse.add_argument(CliOption.FILE.value, help="the file to parse")
        parse.add_argument(
            CliOption.OUTPUT.flag,
            help="save parsed_document.json and .md into this folder; without it, print instead",
        )
        parse.add_argument(
            CliOption.FORMAT.flag,
            choices=[member.value for member in CliFormat],
            default=CliFormat.JSON.value,
            help="what to print when not saving: json (schema v1, default) or markdown",
        )
        parse.add_argument(
            CliOption.SUMMARY.flag,
            action="store_true",
            help="also make the optional summary (off by default)",
        )
