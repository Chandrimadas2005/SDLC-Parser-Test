import sys
from collections.abc import Sequence

from ParserService.Application.UseCases.GenerateOptionalSummary import GenerateOptionalSummary
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Cli.CliArgumentParser import CliArgumentParser
from ParserService.Infrastructure.Cli.CliConsoleOutput import CliConsoleOutput
from ParserService.Infrastructure.Cli.CliDependencies import CliDependencies
from ParserService.Infrastructure.Cli.CliExitCode import CliExitCode
from ParserService.Infrastructure.Cli.CliFileOutput import CliFileOutput
from ParserService.Infrastructure.Cli.CliOutput import CliOutput
from ParserService.Infrastructure.Cli.CliRequest import CliRequest


class ParserCli:
    """``parser-cli parse <file> [--output <folder>] [--format json|markdown] [--summary]``.

    Parses one file with the same type detector, extractors and encoders as the
    worker, without the web server or the database (brief, section 2.4). Without
    ``--output`` the result is printed live and nothing is saved; with it, the
    result is saved as ``parsed_document.json`` and ``parsed_document.md``. The
    optional summary is made only with ``--summary``, and only after the result is
    out, so it can never lose or fail it. Exit codes: 0 succeeded, 2 partial,
    1 failed (see ``CliExitCode``). Status lines and errors go to standard error.
    """

    def __init__(self, dependencies: CliDependencies) -> None:
        self._dependencies = dependencies

    @classmethod
    def main(cls) -> None:
        """Run the command with the process arguments and exit with its code."""
        raise SystemExit(cls(CliDependencies.from_environment()).run(sys.argv[1:]))

    def run(self, arguments: Sequence[str]) -> int:
        """Run the command.

        Args:
            arguments: The command-line arguments, without the program name.

        Returns:
            The exit code.
        """
        options = CliArgumentParser.build().parse_args(arguments)
        request = CliRequest.from_arguments(options)
        return int(self._parse(request, self._output(request)))

    def _output(self, request: CliRequest) -> CliOutput:
        dependencies = self._dependencies
        if request.output is None:
            return CliConsoleOutput(request.output_format, dependencies.renderer, dependencies.out)
        return CliFileOutput(request.output, dependencies.renderer, dependencies.errors)

    def _parse(self, request: CliRequest, output: CliOutput) -> CliExitCode:
        source = request.source
        if not source.is_file():
            self._dependencies.errors.write(f"File not found: {source}\n")
            return CliExitCode.FAILED
        if source.stat().st_size > self._dependencies.limits.max_file_size_bytes:
            return self._fail(request, output, FailureReason.FILE_TOO_LARGE)
        parsed = self._dependencies.pipeline.parse(SourceFile(str(source), FileName(source.name)))
        if parsed.is_err:
            return self._fail(request, output, parsed.unwrap_err())
        return self._succeed(request, output, parsed.unwrap())

    def _succeed(
        self, request: CliRequest, output: CliOutput, document: ParsedDocument
    ) -> CliExitCode:
        if not output.document(document):
            return CliExitCode.FAILED
        if not request.summary:
            return self._done(request, document)
        return self._summarise(request, output, document)

    def _summarise(
        self, request: CliRequest, output: CliOutput, document: ParsedDocument
    ) -> CliExitCode:
        result = GenerateOptionalSummary(self._dependencies.summary_generator).generate(document)
        if result.summary is None:
            self._dependencies.errors.write("Summary unavailable; the parse result is unchanged.\n")
        if not output.summary(result):
            return CliExitCode.FAILED
        return self._done(request, result.document)

    def _fail(self, request: CliRequest, output: CliOutput, reason: FailureReason) -> CliExitCode:
        self._dependencies.errors.write(f"Parsing {request.source} failed: {reason}\n")
        output.failure(FileName(request.source.name), reason)
        return CliExitCode.FAILED

    def _done(self, request: CliRequest, document: ParsedDocument) -> CliExitCode:
        warnings = f", {document.warning_count} warning(s)" if document.warnings else ""
        saved = f" -> {request.output}" if request.output is not None else ""
        self._dependencies.errors.write(f"{document.status}: {request.source}{saved}{warnings}\n")
        return CliExitCode.of(document.status)
