import json
from pathlib import Path
from typing import Final

from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Isolation.IsolatedParseRunner import IsolatedParseRunner
from ParserService.Infrastructure.Output.OutputField import OutputField
from tools.Measurement.MeasurementRow import MeasurementRow


class ParseMeasurement:
    """Parses every file in a folder with the real isolated worker and records its cost.

    This is the script the brief asks for in Phase 0: it measures parse time and
    peak memory per file, so the default limits can be based on real numbers.
    """

    SKIPPED_NAMES: Final = frozenset({"README.md"})
    UNKNOWN: Final = "-"

    def __init__(self, runner: IsolatedParseRunner) -> None:
        self._runner = runner

    def measure(self, folder: Path) -> list[MeasurementRow]:
        """Parse and measure every file below a folder.

        Args:
            folder: The corpus folder.

        Returns:
            One row per file, sorted by path.
        """
        files = sorted(
            path
            for path in folder.rglob("*")
            if path.is_file() and path.name not in self.SKIPPED_NAMES
        )
        return [self._row(folder, path) for path in files]

    def _row(self, folder: Path, path: Path) -> MeasurementRow:
        relative = path.relative_to(folder).as_posix()
        size = path.stat().st_size
        ran = self._runner.run(path, FileName(path.name))
        if ran.is_err:
            return MeasurementRow(relative, self.UNKNOWN, size, ran.unwrap_err().value, None, None)
        worker = ran.unwrap()
        document = json.loads(worker.outcome.content)[OutputField.DOCUMENT]
        detected = str(document[OutputField.DETECTED_TYPE])
        status = worker.outcome.status.value
        return MeasurementRow(
            relative, detected, size, status, worker.elapsed_ms, worker.peak_memory_kb
        )
