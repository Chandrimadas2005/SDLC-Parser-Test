import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import ClassVar, Final

from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.ParseOutcome import ParseOutcome
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Isolation.OutcomeField import OutcomeField
from ParserService.Infrastructure.Isolation.WorkerFile import WorkerFile
from ParserService.Infrastructure.Isolation.WorkerLimits import WorkerLimits
from ParserService.Infrastructure.Isolation.WorkerResult import WorkerResult


class IsolatedParseRunner:
    """Parses one file in its own short-lived worker process (brief, sections 2.5, 2.6).

    The worker caps its own memory and CPU time. The parent also enforces a wall-clock
    timeout and kills the worker when it is exceeded. Whatever happens inside, the
    caller gets a result or a precise failure reason, and other jobs are unaffected.
    The worker's output is never logged.
    """

    MODULE: ClassVar[str] = "ParserService.Infrastructure.Isolation"
    GRACE_SECONDS: ClassVar[int] = 5
    CPU_LIMIT_SIGNALS: Final = frozenset({-signal.SIGXCPU, -signal.SIGKILL})

    def __init__(self, limits: WorkerLimits, temporary_root: Path | None = None) -> None:
        self._limits = limits
        self._temporary_root = temporary_root

    def run(self, source: Path, file_name: FileName) -> Result[WorkerResult, FailureReason]:
        """Parse a file in a fresh worker process.

        Args:
            source: Path of the file to parse.
            file_name: The caller's file name, a hint for detection.

        Returns:
            The result and its cost, or ``timeout``, ``extractor_crash`` or the
            failure reason the worker reported.
        """
        if self._temporary_root is not None:
            self._temporary_root.mkdir(parents=True, exist_ok=True)
        prefix = f"parse-{os.getpid()}-"
        with tempfile.TemporaryDirectory(prefix=prefix, dir=self._temporary_root) as output:
            folder = Path(output)
            exit_code = self._execute([str(source), file_name.value, output])
            if exit_code != 0:
                return Result.err(self._failure_for(exit_code))
            return self._collect(folder)

    def _execute(self, arguments: list[str]) -> int | None:
        limits = [str(self._limits.memory_mb), str(self._limits.timeout_seconds)]
        command = [sys.executable, "-m", self.MODULE, *arguments, *limits]
        try:
            completed = subprocess.run(  # noqa: S603 - fixed command, no shell
                command,
                capture_output=True,
                timeout=self._limits.timeout_seconds + self.GRACE_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None
        return completed.returncode

    def _failure_for(self, exit_code: int | None) -> FailureReason:
        if exit_code is None or exit_code in self.CPU_LIMIT_SIGNALS:
            return FailureReason.TIMEOUT
        return FailureReason.EXTRACTOR_CRASH

    @staticmethod
    def _collect(folder: Path) -> Result[WorkerResult, FailureReason]:
        failure = folder / WorkerFile.FAILURE
        if failure.exists():
            return Result.err(FailureReason(failure.read_text(encoding="utf-8").strip()))
        result, outcome = folder / WorkerFile.RESULT, folder / WorkerFile.OUTCOME
        if not (result.exists() and outcome.exists()):
            return Result.err(FailureReason.EXTRACTOR_CRASH)
        fields = json.loads(outcome.read_text(encoding="utf-8"))
        status = DocumentStatus(fields[OutcomeField.STATUS])
        parsed = ParseOutcome(status, int(fields[OutcomeField.WARNING_COUNT]), result.read_bytes())
        elapsed, memory = (
            int(fields[OutcomeField.ELAPSED_MS]),
            int(fields[OutcomeField.PEAK_MEMORY_KB]),
        )
        return Result.ok(WorkerResult(parsed, elapsed, memory))
