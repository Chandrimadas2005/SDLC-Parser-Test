import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Self, TextIO

from ParserService.Infrastructure.Config.Limits import Limits
from ParserService.Infrastructure.Isolation.IsolatedParseRunner import IsolatedParseRunner
from ParserService.Infrastructure.Isolation.WorkerLimits import WorkerLimits
from tools.Measurement.MeasurementReport import MeasurementReport
from tools.Measurement.ParseMeasurement import ParseMeasurement


class MeasurementCli:
    """``python -m tools.Measurement <corpus folder> <report file>``."""

    EXIT_OK: Final = 0
    EXIT_USAGE: Final = 2
    ARGUMENT_COUNT: Final = 2
    USAGE: Final = "usage: python -m tools.Measurement <corpus folder> <report file>\n"

    def __init__(self, measurement: ParseMeasurement, output: TextIO) -> None:
        self._measurement = measurement
        self._output = output

    @classmethod
    def default(cls, output: TextIO | None = None) -> Self:
        """Build the command with the service's default limits.

        Args:
            output: Where the summary is written; standard output when omitted.

        Returns:
            A ready-to-run command.
        """
        limits = Limits()
        worker = WorkerLimits(
            limits.job_timeout_seconds, limits.job_memory_limit_mb, limits.max_pages
        )
        return cls(ParseMeasurement(IsolatedParseRunner(worker)), output or sys.stdout)

    def run(self, arguments: Sequence[str]) -> int:
        """Measure a folder and write the report.

        Args:
            arguments: The corpus folder and the report file.

        Returns:
            ``EXIT_OK``, or ``EXIT_USAGE`` when the arguments are wrong.
        """
        if len(arguments) != self.ARGUMENT_COUNT or not Path(arguments[0]).is_dir():
            self._output.write(self.USAGE)
            return self.EXIT_USAGE
        rows = self._measurement.measure(Path(arguments[0]))
        Path(arguments[1]).write_text(MeasurementReport().render(rows), encoding="utf-8")
        self._output.write(f"measured {len(rows)} files into {arguments[1]}\n")
        return self.EXIT_OK
