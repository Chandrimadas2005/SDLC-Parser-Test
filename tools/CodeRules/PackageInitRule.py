import ast
from pathlib import Path
from typing import Final

from tools.CodeRules.RuleName import RuleName
from tools.CodeRules.SourceFile import SourceFile
from tools.CodeRules.Violation import Violation


class PackageInitRule:
    """Checks that every package has an ``__init__.py`` declaring ``__all__``.

    Also rejects catch-all packages named ``utils`` or ``common``.
    """

    INIT_FILE_NAME: Final = "__init__.py"
    ALL_NAME: Final = "__all__"
    FORBIDDEN_NAMES: Final = frozenset({"utils", "common"})

    def check(self, directory: Path) -> list[Violation]:
        """Find package violations in one directory that holds Python files.

        Args:
            directory: Package directory to check.

        Returns:
            At most one violation describing the first problem found.
        """
        if directory.name.lower() in self.FORBIDDEN_NAMES:
            message = f"no '{directory.name}' packages; name the package after what it does"
            return [Violation(directory, 1, RuleName.FORBIDDEN_PACKAGE, message)]
        init_file = directory / self.INIT_FILE_NAME
        if not init_file.is_file():
            return [Violation(directory, 1, RuleName.PACKAGE_INIT, "package has no __init__.py")]
        return self._all_violations(SourceFile.load(init_file))

    def _all_violations(self, init_source: SourceFile) -> list[Violation]:
        names = {target.id for node in init_source.tree.body for target in self._names(node)}
        if self.ALL_NAME in names:
            return []
        return [
            Violation(init_source.path, 1, RuleName.PACKAGE_ALL, "__init__.py must declare __all__")
        ]

    @staticmethod
    def _names(node: ast.stmt) -> list[ast.Name]:
        match node:
            case ast.Assign(targets=targets):
                return [target for target in targets if isinstance(target, ast.Name)]
            case ast.AnnAssign(target=ast.Name() as target):
                return [target]
            case _:
                return []
