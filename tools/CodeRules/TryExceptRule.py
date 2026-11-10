import ast
from typing import ClassVar, Final

from tools.CodeRules.FunctionNodes import FunctionNodes
from tools.CodeRules.RuleName import RuleName
from tools.CodeRules.SourceFile import SourceFile
from tools.CodeRules.Violation import Violation


class TryExceptRule:
    """Flags functions that contain more than one ``try`` statement.

    Nested functions and classes are counted separately, so a ``try`` inside a nested
    function never counts against the outer one.
    """

    MAX_TRY_STATEMENTS: Final = 1
    TRY_TYPES: ClassVar[tuple[type[ast.AST], ...]] = (ast.Try, ast.TryStar)

    def __init__(self, function_nodes: FunctionNodes) -> None:
        self._function_nodes = function_nodes

    def check(self, source: SourceFile) -> list[Violation]:
        """Find the functions in a file that use more than one ``try``.

        Args:
            source: Parsed file to check.

        Returns:
            One violation per function with too many ``try`` statements.
        """
        counted = [
            (node, self._try_count(node)) for node in self._function_nodes.functions(source.tree)
        ]
        return [
            Violation(source.path, node.lineno, RuleName.TRY_PER_METHOD, self._message(node, count))
            for node, count in counted
            if count > self.MAX_TRY_STATEMENTS
        ]

    def _try_count(self, function: ast.AST) -> int:
        return sum(
            isinstance(node, self.TRY_TYPES) for node in self._function_nodes.own_nodes(function)
        )

    def _message(self, node: ast.FunctionDef | ast.AsyncFunctionDef, count: int) -> str:
        return f"'{node.name}' has {count} try statements; split it so each method has one"
