import json
import sys
from pathlib import Path

import pytest

from ParserService.Domain.Errors import Result
from ParserService.Infrastructure.Cli import CliDependencies, CliExitCode, ParserCli
from ParserService.Infrastructure.Config import EnvironmentVariable, Limits
from ParserService.Infrastructure.Output import (
    ParsedDocumentJsonEncoder,
    ParsedDocumentMarkdownRenderer,
)
from tests.Fakes import FakeSummaryGenerator
from tests.Infrastructure.Cli.CliHarness import CliHarness
from tests.Samples import DocumentSamples


class TestParserCli:
    """Without --output, parser-cli prints the result live and saves nothing."""

    @pytest.mark.parametrize("source", [CliHarness.ARTICLE, CliHarness.WORKBOOK])
    def test_the_result_is_printed_as_json_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
    ) -> None:
        monkeypatch.chdir(tmp_path)
        harness = CliHarness()

        exit_code = harness.run("parse", str(source))

        assert exit_code == CliExitCode.SUCCEEDED
        assert harness.out.getvalue() == ParsedDocumentJsonEncoder().to_json(harness.parsed(source))
        assert list(tmp_path.iterdir()) == []
        assert harness.errors.getvalue().startswith(f"succeeded: {source}")

    def test_markdown_can_be_printed_instead(self) -> None:
        harness = CliHarness()

        harness.run("parse", str(CliHarness.ARTICLE), "--format", "markdown")

        encoded = ParsedDocumentJsonEncoder().to_json(harness.parsed(CliHarness.ARTICLE))
        expected = ParsedDocumentMarkdownRenderer().render(encoded.encode())
        assert harness.out.getvalue() == expected

    def test_no_summary_is_made_unless_asked_for(self) -> None:
        generator = FakeSummaryGenerator()
        harness = CliHarness(generator=generator)

        harness.run("parse", str(CliHarness.ARTICLE))

        assert generator.documents == []
        assert "Summary of" not in harness.out.getvalue()

    def test_the_summary_follows_the_result_when_asked_for(self) -> None:
        harness = CliHarness()

        exit_code = harness.run("parse", str(CliHarness.WORKBOOK), "--summary")

        document, summary = harness.out.getvalue().split("\n# Summary of normal.ods\n\n")
        assert exit_code == CliExitCode.SUCCEEDED
        assert json.loads(document)["status"] == "succeeded"
        assert summary.startswith("normal.ods (ODS, ")

    def test_a_failing_summary_never_fails_the_parse(self) -> None:
        harness = CliHarness(generator=FakeSummaryGenerator(error=RuntimeError("down")))

        exit_code = harness.run("parse", str(CliHarness.ARTICLE), "--summary")

        assert exit_code == CliExitCode.SUCCEEDED
        assert json.loads(harness.out.getvalue())["status"] == "succeeded"
        assert "Summary unavailable" in harness.errors.getvalue()

    def test_a_partial_result_exits_with_two(self) -> None:
        partial = DocumentSamples().spreadsheet()
        harness = CliHarness(pipeline=CliHarness.pipeline_returning(Result.ok(partial)))

        assert harness.run("parse", str(CliHarness.ARTICLE)) == CliExitCode.PARTIAL
        assert json.loads(harness.out.getvalue())["status"] == "partial"

    @pytest.mark.parametrize(
        ("source", "reason"),
        [(CliHarness.TRUNCATED, "corrupted_file"), (CliHarness.ARTICLE, "file_too_large")],
    )
    def test_a_failure_prints_its_reason_and_exits_with_one(
        self, source: Path, reason: str
    ) -> None:
        harness = CliHarness(limits=Limits(max_file_size_bytes=1_000))

        exit_code = harness.run("parse", str(source))

        assert exit_code == CliExitCode.FAILED
        assert json.loads(harness.out.getvalue())["failure_reason"] == reason
        assert f"failed: {reason}" in harness.errors.getvalue()

    def test_an_unsupported_file_prints_markdown_when_asked(self, tmp_path: Path) -> None:
        source = tmp_path / "scan.png"
        source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
        harness = CliHarness()

        exit_code = harness.run("parse", str(source), "--format", "markdown")

        assert exit_code == CliExitCode.FAILED
        assert harness.out.getvalue().endswith("- Failure reason: `unsupported_type`\n")

    def test_a_missing_file_prints_nothing_to_standard_output(self, tmp_path: Path) -> None:
        harness = CliHarness()

        exit_code = harness.run("parse", str(tmp_path / "missing.html"))

        assert exit_code == CliExitCode.FAILED
        assert harness.out.getvalue() == ""
        assert "File not found" in harness.errors.getvalue()

    @pytest.mark.parametrize(
        "arguments",
        [[], ["parse"], ["parse", "a.html", "--format", "xml"], ["unknown", "a.html"]],
    )
    def test_wrong_arguments_exit_with_one_not_the_partial_code(self, arguments: list[str]) -> None:
        with pytest.raises(SystemExit) as raised:
            CliHarness().run(*arguments)

        assert raised.value.code == CliExitCode.FAILED

    def test_help_exits_cleanly(self) -> None:
        with pytest.raises(SystemExit) as raised:
            CliHarness().run("parse", "--help")

        assert raised.value.code == 0

    def test_main_prints_to_the_real_standard_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["parser-cli", "parse", str(CliHarness.ARTICLE)])

        with pytest.raises(SystemExit) as raised:
            ParserCli.main()

        captured = capsys.readouterr()
        assert raised.value.code == CliExitCode.SUCCEEDED
        assert json.loads(captured.out)["document"]["file_name"] == "article.html"
        assert captured.err.startswith("succeeded:")

    def test_dependencies_read_limits_from_the_environment(self) -> None:
        dependencies = CliDependencies.from_environment(
            {EnvironmentVariable.MAX_FILE_SIZE_BYTES: "7"}
        )

        assert dependencies.limits.max_file_size_bytes == 7
