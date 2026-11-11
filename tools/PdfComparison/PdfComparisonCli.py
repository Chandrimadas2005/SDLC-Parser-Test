import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Self, TextIO

from tools.PdfComparison.ComparisonReport import ComparisonReport
from tools.PdfComparison.PdfComparisonRunner import PdfComparisonRunner
from tools.PdfComparison.PdfTextExtraction import PdfTextExtraction
from tools.PdfComparison.SyntheticPdfFactory import SyntheticPdfFactory


class PdfComparisonCli:
    """``python -m tools.PdfComparison <report file> [page counts...]``."""

    EXIT_OK: Final = 0
    EXIT_USAGE: Final = 2
    DEFAULT_PAGE_COUNTS: Final = (1, 20, 200)
    USAGE: Final = "usage: python -m tools.PdfComparison <report file> [page counts...]\n"

    def __init__(
        self, factory: SyntheticPdfFactory, runner: PdfComparisonRunner, output: TextIO
    ) -> None:
        self._factory = factory
        self._runner = runner
        self._output = output

    @classmethod
    def default(cls, output: TextIO | None = None) -> Self:
        """Build the command.

        Args:
            output: Where the summary is written; standard output when omitted.

        Returns:
            A ready-to-run command.
        """
        runner = PdfComparisonRunner(PdfTextExtraction())
        return cls(SyntheticPdfFactory(), runner, output or sys.stdout)

    def run(self, arguments: Sequence[str]) -> int:
        """Generate samples, compare the libraries and write the report.

        Args:
            arguments: The report file, then optional page counts.

        Returns:
            ``EXIT_OK``, or ``EXIT_USAGE`` when the arguments are wrong.
        """
        if not arguments or not all(count.isdigit() for count in arguments[1:]):
            self._output.write(self.USAGE)
            return self.EXIT_USAGE
        counts = [int(count) for count in arguments[1:]] or list(self.DEFAULT_PAGE_COUNTS)
        with tempfile.TemporaryDirectory(prefix="pdf-comparison-") as folder:
            samples = [self._factory.create(Path(folder) / f"{n}.pdf", n) for n in counts]
            results = [result for sample in samples for result in self._runner.compare(sample)]
        Path(arguments[0]).write_text(ComparisonReport().render(results), encoding="utf-8")
        self._output.write(f"compared {len(counts)} samples into {arguments[0]}\n")
        return self.EXIT_OK
