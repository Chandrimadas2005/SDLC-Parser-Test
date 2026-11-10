from collections.abc import Sequence
from pathlib import Path
from typing import Final

from tools.CodeRules.FileRule import FileRule
from tools.CodeRules.PackageRule import PackageRule
from tools.CodeRules.SourceFile import SourceFile
from tools.CodeRules.Violation import Violation


class CodeRulesChecker:
    """Applies every file rule and package rule to the Python files under some roots."""

    IGNORED_DIRECTORIES: Final = frozenset({".venv", "venv", "__pycache__", "build", "dist"})

    def __init__(
        self, file_rules: Sequence[FileRule], package_rules: Sequence[PackageRule]
    ) -> None:
        self._file_rules = tuple(file_rules)
        self._package_rules = tuple(package_rules)

    def check(self, roots: Sequence[Path]) -> list[Violation]:
        """Check every Python file and package below the given roots.

        Args:
            roots: Directories to scan recursively.

        Returns:
            All violations, file rules first, each group sorted by path.
        """
        files = sorted(
            path for root in roots for path in root.rglob("*.py") if self._is_checked(path)
        )
        packages = sorted({path.parent for path in files})
        file_violations = [violation for path in files for violation in self._check_file(path)]
        package_violations = [
            violation for path in packages for violation in self._check_package(path)
        ]
        return file_violations + package_violations

    def _is_checked(self, path: Path) -> bool:
        return self.IGNORED_DIRECTORIES.isdisjoint(path.parts)

    def _check_file(self, path: Path) -> list[Violation]:
        source = SourceFile.load(path)
        return [violation for rule in self._file_rules for violation in rule.check(source)]

    def _check_package(self, directory: Path) -> list[Violation]:
        return [violation for rule in self._package_rules for violation in rule.check(directory)]
