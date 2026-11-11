import io
from pathlib import Path

from tools.PdfComparison import PdfComparisonCli, PdfLibrary, SyntheticPdfFactory


class TestPdfComparisonCli:
    """The comparison generates known PDFs and scores every library on them."""

    def test_report_scores_every_library(self, tmp_path: Path) -> None:
        report, output = tmp_path / "report.md", io.StringIO()

        exit_code = PdfComparisonCli.default(output).run([str(report), "2"])

        text = report.read_text(encoding="utf-8")
        assert exit_code == PdfComparisonCli.EXIT_OK
        for library in PdfLibrary:
            assert f"| {library.value} | 2 |" in text
        assert "100.0% | 100.0% |" in text
        assert output.getvalue() == f"compared 1 samples into {report}\n"

    def test_wrong_arguments_print_usage(self) -> None:
        output = io.StringIO()

        assert PdfComparisonCli.default(output).run(["report.md", "many"]) == 2
        assert output.getvalue() == PdfComparisonCli.USAGE

    def test_factory_knows_the_words_of_every_page(self, tmp_path: Path) -> None:
        sample = SyntheticPdfFactory().create(tmp_path / "s.pdf", 3)

        assert sample.page_count == 3
        assert sample.expected_pages[0][:3] == ("Synthetic", "heading", "1")
        assert sample.path.read_bytes().startswith(b"%PDF")
