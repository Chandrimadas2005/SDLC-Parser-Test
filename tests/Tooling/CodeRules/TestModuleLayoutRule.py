from pathlib import Path

import pytest

from tools.CodeRules import ModuleLayoutRule, RuleName, SourceFile


class TestModuleLayoutRule:
    """One public class per file, named like the file, and no top-level functions."""

    @staticmethod
    def _check(file_name: str, text: str) -> list[RuleName]:
        source = SourceFile.parse(Path("pkg") / file_name, text)
        return [violation.rule for violation in ModuleLayoutRule().check(source)]

    def test_single_class_named_like_the_file_passes(self) -> None:
        assert self._check("Widget.py", "class Widget:\n    pass\nclass _Helper:\n    pass\n") == []

    def test_class_named_differently_from_the_file_is_reported(self) -> None:
        assert self._check("Widget.py", "class Gadget:\n    pass\n") == [
            RuleName.FILE_NAME_MATCHES_CLASS
        ]

    @pytest.mark.parametrize(
        "text", ["X = 1\n", "class A:\n    pass\nclass B:\n    pass\n"], ids=["none", "two"]
    )
    def test_file_without_exactly_one_public_class_is_reported(self, text: str) -> None:
        assert self._check("A.py", text) == [RuleName.ONE_PUBLIC_CLASS]

    def test_top_level_function_is_reported(self) -> None:
        text = "def helper() -> None:\n    pass\nclass Widget:\n    pass\n"

        assert self._check("Widget.py", text) == [RuleName.TOP_LEVEL_FUNCTION]

    @pytest.mark.parametrize("file_name", ["__init__.py", "__main__.py", "conftest.py", "env.py"])
    def test_package_and_entry_point_files_are_exempt(self, file_name: str) -> None:
        assert self._check(file_name, "def main() -> None:\n    pass\n") == []
