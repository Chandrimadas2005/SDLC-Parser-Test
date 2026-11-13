import json
from pathlib import Path

import pytest

from ParserService.Infrastructure.Cli import CliExitCode, CliOutputFile
from ParserService.Infrastructure.Output import ParsedDocumentJsonEncoder
from tests.Fakes import FakeSummaryGenerator
from tests.Infrastructure.Cli.CliHarness import CliHarness


class TestParserCliFileOutput:
    """With --output (brief, section 2.4), parser-cli saves its results into a folder."""

    @staticmethod
    def _json(folder: Path) -> dict[str, object]:
        loaded = json.loads((folder / CliOutputFile.DOCUMENT_JSON).read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)
        return loaded

    @staticmethod
    def _names(folder: Path) -> list[str]:
        return sorted(path.name for path in folder.iterdir())

    @pytest.mark.parametrize("source", [CliHarness.ARTICLE, CliHarness.WORKBOOK])
    def test_the_result_is_saved_as_json_and_markdown(self, tmp_path: Path, source: Path) -> None:
        harness = CliHarness()
        output = tmp_path / "out" / "nested"

        exit_code = harness.run("parse", str(source), "--output", str(output))

        assert exit_code == CliExitCode.SUCCEEDED
        assert self._names(output) == [CliOutputFile.DOCUMENT_JSON, CliOutputFile.DOCUMENT_MARKDOWN]
        saved = (output / CliOutputFile.DOCUMENT_JSON).read_text(encoding="utf-8")
        assert saved == ParsedDocumentJsonEncoder().to_json(harness.parsed(source))
        assert harness.out.getvalue() == ""
        assert harness.errors.getvalue().startswith(f"succeeded: {source} -> {output}")

    def test_text_is_saved_as_utf8(self, tmp_path: Path) -> None:
        CliHarness().run("parse", str(CliHarness.ARTICLE), "--output", str(tmp_path))

        raw = (tmp_path / CliOutputFile.DOCUMENT_JSON).read_bytes()
        assert "Café naïve résumé".encode() in raw

    def test_the_summary_is_saved_only_when_asked_for(self, tmp_path: Path) -> None:
        harness = CliHarness()

        harness.run("parse", str(CliHarness.WORKBOOK), "--output", str(tmp_path), "--summary")
        summary = (tmp_path / CliOutputFile.SUMMARY).read_text(encoding="utf-8")
        harness.run("parse", str(CliHarness.WORKBOOK), "--output", str(tmp_path))

        assert summary.startswith("# Summary of normal.ods\n\nnormal.ods (ODS, ")
        assert CliOutputFile.SUMMARY not in self._names(tmp_path)

    def test_a_failing_summary_is_recorded_as_a_warning(self, tmp_path: Path) -> None:
        harness = CliHarness(generator=FakeSummaryGenerator(error=RuntimeError("down")))

        exit_code = harness.run(
            "parse", str(CliHarness.ARTICLE), "--output", str(tmp_path), "--summary"
        )

        warnings = self._json(tmp_path)["warnings"]
        assert isinstance(warnings, list)
        assert exit_code == CliExitCode.SUCCEEDED
        assert warnings[-1] == {"code": "summary_unavailable"}
        assert CliOutputFile.SUMMARY not in self._names(tmp_path)

    def test_a_failure_saves_its_reason(self, tmp_path: Path) -> None:
        harness = CliHarness()

        exit_code = harness.run("parse", str(CliHarness.TRUNCATED), "--output", str(tmp_path))

        assert exit_code == CliExitCode.FAILED
        assert self._json(tmp_path) == {
            "schema_version": "1.2",
            "status": "failed",
            "failure_reason": "corrupted_file",
            "document": {"file_name": "truncated.ods"},
        }
        markdown = (tmp_path / CliOutputFile.DOCUMENT_MARKDOWN).read_text(encoding="utf-8")
        assert markdown.endswith("- Failure reason: `corrupted_file`\n")

    def test_a_missing_file_saves_nothing(self, tmp_path: Path) -> None:
        output = tmp_path / "out"

        exit_code = CliHarness().run("parse", str(tmp_path / "gone.html"), "--output", str(output))

        assert exit_code == CliExitCode.FAILED
        assert not output.exists()

    def test_an_unwritable_folder_fails(self, tmp_path: Path) -> None:
        blocker = tmp_path / "occupied"
        blocker.write_text("a file, not a folder", encoding="utf-8")
        harness = CliHarness()

        exit_code = harness.run("parse", str(CliHarness.ARTICLE), "--output", str(blocker))

        assert exit_code == CliExitCode.FAILED
        assert "Could not write output" in harness.errors.getvalue()
