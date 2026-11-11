import io
from pathlib import Path

from ParserService.Infrastructure.Isolation import IsolatedParseRunner, WorkerLimits
from tools.Measurement import MeasurementCli, MeasurementReport, MeasurementRow, ParseMeasurement


class TestMeasurementCli:
    """The script measures every corpus file with the real worker and writes a report."""

    @staticmethod
    def _cli(output: io.StringIO) -> MeasurementCli:
        runner = IsolatedParseRunner(WorkerLimits(timeout_seconds=30, memory_mb=1024))
        return MeasurementCli(ParseMeasurement(runner), output)

    def test_report_lists_every_file_with_its_cost(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        (corpus / "notes.txt").write_text("Synthetic text.\n", encoding="utf-8")
        (corpus / "blob.bin").write_bytes(bytes(range(256)) * 4)
        (corpus / "README.md").write_text("ignored\n", encoding="utf-8")
        report, output = tmp_path / "report.md", io.StringIO()

        assert self._cli(output).run([str(corpus), str(report)]) == MeasurementCli.EXIT_OK

        text = report.read_text(encoding="utf-8")
        assert "| notes.txt | txt | 16 | succeeded |" in text
        assert "| blob.bin | - | 1024 | unsupported_type | - | - |" in text
        assert "README" not in text
        assert output.getvalue() == f"measured 2 files into {report}\n"

    def test_wrong_arguments_print_usage(self, tmp_path: Path) -> None:
        output = io.StringIO()

        exit_code = self._cli(output).run([str(tmp_path / "missing"), "out.md"])

        assert exit_code == MeasurementCli.EXIT_USAGE
        assert output.getvalue() == MeasurementCli.USAGE

    def test_summary_keeps_the_worst_case_per_type(self) -> None:
        rows = [
            MeasurementRow("a.txt", "txt", 1, "succeeded", 5, 2048),
            MeasurementRow("b.txt", "txt", 1, "succeeded", 9, 1024),
        ]

        assert "| txt | 2 | 9 | 2.0 |" in MeasurementReport().render(rows)
