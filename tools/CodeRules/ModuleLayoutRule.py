import ast
from typing import Final

from tools.CodeRules.RuleName import RuleName
from tools.CodeRules.SourceFile import SourceFile
from tools.CodeRules.Violation import Violation


class ModuleLayoutRule:
    """Checks the file layout rules: one public class per file, named like the file.

    Also forbids top-level functions; behaviour belongs in classes. Package markers,
    ``__main__`` entry points, pytest ``conftest`` files and Alembic's ``env.py`` script
    (which must be a script, so it delegates to a class in one line) are exempt.
    """

    EXEMPT_FILE_NAMES: Final = frozenset({"__init__.py", "__main__.py", "conftest.py", "env.py"})

    def check(self, source: SourceFile) -> list[Violation]:
        """Find layout violations in a file.

        Args:
            source: Parsed file to check.

        Returns:
            Violations for top-level functions and for the public class layout.
        """
        if source.path.name in self.EXEMPT_FILE_NAMES:
            return []
        return [*self._top_level_functions(source), *self._class_layout(source)]

    @staticmethod
    def _top_level_functions(source: SourceFile) -> list[Violation]:
        return [
            Violation(
                source.path,
                node.lineno,
                RuleName.TOP_LEVEL_FUNCTION,
                f"top-level function '{node.name}'; move it into a class",
            )
            for node in source.tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        ]

    @staticmethod
    def _class_layout(source: SourceFile) -> list[Violation]:
        public = [
            node
            for node in source.tree.body
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
        ]
        if len(public) != 1:
            message = f"expected exactly one public class, found {len(public)}"
            return [Violation(source.path, 1, RuleName.ONE_PUBLIC_CLASS, message)]
        if public[0].name != source.path.stem:
            message = f"class '{public[0].name}' must be in a file named '{public[0].name}.py'"
            return [
                Violation(source.path, public[0].lineno, RuleName.FILE_NAME_MATCHES_CLASS, message)
            ]
        return []
