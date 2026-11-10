from pathlib import Path

import pytest

from tools.CodeRules import PackageInitRule, RuleName


class TestPackageInitRule:
    """Every package has an __init__.py with __all__, and no utils/common packages exist."""

    @staticmethod
    def _package(root: Path, name: str, init_text: str | None) -> Path:
        directory = root / name
        directory.mkdir()
        if init_text is not None:
            (directory / "__init__.py").write_text(init_text, encoding="utf-8")
        return directory

    @pytest.mark.parametrize(
        "init_text", ['__all__ = ["A"]\n', "__all__: list[str] = []\n"], ids=["plain", "annotated"]
    )
    def test_init_declaring_all_passes(self, tmp_path: Path, init_text: str) -> None:
        directory = self._package(tmp_path, "Jobs", init_text)

        assert PackageInitRule().check(directory) == []

    def test_missing_init_is_reported(self, tmp_path: Path) -> None:
        directory = self._package(tmp_path, "Jobs", None)

        assert [v.rule for v in PackageInitRule().check(directory)] == [RuleName.PACKAGE_INIT]

    def test_init_without_all_is_reported(self, tmp_path: Path) -> None:
        directory = self._package(tmp_path, "Jobs", '"""Doc."""\nX = 1\nY: int = 2\n')

        assert [v.rule for v in PackageInitRule().check(directory)] == [RuleName.PACKAGE_ALL]

    @pytest.mark.parametrize("name", ["utils", "Common"])
    def test_catch_all_package_names_are_reported(self, tmp_path: Path, name: str) -> None:
        directory = self._package(tmp_path, name, "__all__ = []\n")

        assert [v.rule for v in PackageInitRule().check(directory)] == [RuleName.FORBIDDEN_PACKAGE]
