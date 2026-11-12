import json
import resource
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Detection.MagicTypeDetector import MagicTypeDetector
from ParserService.Infrastructure.Detection.TextEncodingDetector import TextEncodingDetector
from ParserService.Infrastructure.Detection.ZipContentInspector import ZipContentInspector
from ParserService.Infrastructure.Extraction.ExtractorRegistry import ExtractorRegistry
from ParserService.Infrastructure.Extraction.ParsePipeline import ParsePipeline
from ParserService.Infrastructure.Isolation.OutcomeField import OutcomeField
from ParserService.Infrastructure.Isolation.WorkerFile import WorkerFile
from ParserService.Infrastructure.Output.ParsedDocumentJsonEncoder import (
    ParsedDocumentJsonEncoder,
)


class ParseWorkerProcess:
    """The code that runs inside one isolated worker process, for one file.

    It first caps its own memory and CPU time, then parses the file and writes the
    result into its output folder. It never catches unexpected errors: a crash
    simply ends the process, and the parent turns that into ``extractor_crash``.

    Arguments: source path, file name, output folder, memory limit (MB), CPU limit (s),
    page limit (0 for none).
    """

    ARGUMENT_COUNT: Final = 6
    BYTES_PER_MB: Final = 1024 * 1024

    def __init__(self, max_pages: int | None = None) -> None:
        self._max_pages = max_pages

    def run(self, arguments: Sequence[str]) -> int:
        """Parse one file under limits and write the result files.

        Args:
            arguments: The six command-line arguments.

        Returns:
            The process exit code: 0 when the result or failure file was written.
        """
        if len(arguments) != self.ARGUMENT_COUNT:
            return 2
        source, name, output, memory_mb, cpu_seconds, max_pages = arguments
        self._limit(int(memory_mb), int(cpu_seconds))
        worker = type(self)(int(max_pages) or None)
        worker.execute(SourceFile(source, FileName(name)), Path(output))
        return 0

    def execute(self, source: SourceFile, folder: Path) -> None:
        """Parse a file and write the result, or the failure reason, into a folder.

        Args:
            source: The file to parse.
            folder: Where to write ``result.json`` and ``outcome.json``, or ``failure.txt``.
        """
        started = time.perf_counter()
        parsed = self._pipeline(self._max_pages).parse(source)
        if parsed.is_err:
            (folder / WorkerFile.FAILURE).write_text(parsed.unwrap_err().value, encoding="utf-8")
            return
        self._write(parsed.unwrap(), folder, started)

    def _limit(self, memory_mb: int, cpu_seconds: int) -> None:
        memory = memory_mb * self.BYTES_PER_MB
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

    @staticmethod
    def _pipeline(max_pages: int | None) -> ParsePipeline:
        detector = MagicTypeDetector(TextEncodingDetector(), ZipContentInspector())
        return ParsePipeline(detector, ExtractorRegistry.default(max_pages))

    @staticmethod
    def _write(document: ParsedDocument, folder: Path, started: float) -> None:
        encoded = ParsedDocumentJsonEncoder().to_json(document)
        (folder / WorkerFile.RESULT).write_text(encoded, encoding="utf-8")
        outcome = {
            OutcomeField.STATUS: document.status.value,
            OutcomeField.WARNING_COUNT: document.warning_count,
            OutcomeField.ELAPSED_MS: round((time.perf_counter() - started) * 1000),
            OutcomeField.PEAK_MEMORY_KB: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
        (folder / WorkerFile.OUTCOME).write_text(json.dumps(outcome), encoding="utf-8")
