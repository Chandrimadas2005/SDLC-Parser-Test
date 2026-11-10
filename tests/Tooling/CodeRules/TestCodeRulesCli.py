import io
from pathlib import Path

from tools.CodeRules import CodeRulesCli


class TestCodeRulesCli:
    """The command checks directories end to end and sets the exit status."""

    @staticmethod
    def _write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def _run(root: Path) -> tuple[int, str]:
        output = io.StringIO()
        status = CodeRulesCli.default(output).run([str(root)])
        return status, output.getvalue()

    def test_compliant_tree_exits_clean(self, tmp_path: Path) -> None:
        self._write(tmp_path / "pkg" / "__init__.py", "__all__ = []\n")
        self._write(tmp_path / "pkg" / "Widget.py", "class Widget:\n    pass\n")

        assert self._run(tmp_path) == (CodeRulesCli.EXIT_CLEAN, "")

    def test_violations_are_printed_and_fail_the_run(self, tmp_path: Path) -> None:
        self._write(tmp_path / "pkg" / "Widget.py", "def helper() -> None:\n    pass\n")

        status, output = self._run(tmp_path)

        assert status == CodeRulesCli.EXIT_VIOLATIONS
        assert "pkg/Widget.py:1: CR003" in output
        assert "CR004" in output
        assert output.rstrip().endswith("CR006 package has no __init__.py")

    def test_virtualenv_and_cache_directories_are_skipped(self, tmp_path: Path) -> None:
        self._write(tmp_path / ".venv" / "lib" / "bad.py", "def helper() -> None:\n    pass\n")

        assert self._run(tmp_path) == (CodeRulesCli.EXIT_CLEAN, "")
