import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self, TextIO

from ParserService.Domain.Ports.SummaryGenerator import SummaryGenerator
from ParserService.Infrastructure.Cli.CliRenderer import CliRenderer
from ParserService.Infrastructure.Config.Limits import Limits
from ParserService.Infrastructure.Config.Settings import Settings
from ParserService.Infrastructure.Extraction.ParsePipeline import ParsePipeline
from ParserService.Infrastructure.Output.ParsedDocumentJsonEncoder import (
    ParsedDocumentJsonEncoder,
)
from ParserService.Infrastructure.Output.ParsedDocumentMarkdownRenderer import (
    ParsedDocumentMarkdownRenderer,
)
from ParserService.Infrastructure.Summary.ExtractiveSummaryGenerator import (
    ExtractiveSummaryGenerator,
)


@dataclass(frozen=True, slots=True)
class CliDependencies:
    """Everything ``parser-cli`` works with, built once at start-up.

    The pipeline is the same one the worker uses. Limits come from the same
    environment variables as the service, so ``PARSER_MAX_FILE_SIZE_BYTES`` and the
    archive limits apply to the command line tool too. Results go to ``out``;
    status lines and errors go to ``errors``.
    """

    pipeline: ParsePipeline
    renderer: CliRenderer
    summary_generator: SummaryGenerator
    limits: Limits
    out: TextIO
    errors: TextIO

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Self:
        """Build the dependencies for a real run.

        Args:
            environment: The environment variables; ``os.environ`` when not given.

        Returns:
            The dependencies, printing results to stdout and messages to stderr.
        """
        variables = os.environ if environment is None else environment
        limits = Settings.from_environment(variables).limits
        return cls(
            pipeline=ParsePipeline.default(limits),
            renderer=CliRenderer(ParsedDocumentJsonEncoder(), ParsedDocumentMarkdownRenderer()),
            summary_generator=ExtractiveSummaryGenerator(),
            limits=limits,
            out=sys.stdout,
            errors=sys.stderr,
        )
