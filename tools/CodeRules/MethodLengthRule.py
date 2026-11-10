import ast
from typing import Final

from tools.CodeRules.FunctionNodes import FunctionNodes
from tools.CodeRules.RuleName import RuleName
from tools.CodeRules.SourceFile import SourceFile
from tools.CodeRules.Violation import Violation


class MethodLengthRule:
    """Flags functions whose body is longer than the allowed number of lines.

    The body is counted from the first statement after the docstring to the last line
    of the function. Blank lines and comment-only lines are not counted, so docstrings
    and spacing never push a method over the limit.
    """

    MAX_LINES: Final = 18

    def __init__(self, function_nodes: FunctionNodes) -> None:
        self._function_nodes = function_nodes

    def check(self, source: SourceFile) -> list[Violation]:
        """Find the functions in a file that are too long.

        Args:
            source: Parsed file to check.

        Returns:
            One violation per function longer than ``MAX_LINES``.
        """
        measured = [(node, self._body_length(source, node)) for node in self._functions(source)]
        return [
            Violation(source.path, node.lineno, RuleName.METHOD_LENGTH, self._message(node, length))
            for node, length in measured
            if length > self.MAX_LINES
        ]

    def _functions(self, source: SourceFile) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        return self._function_nodes.functions(source.tree)

    def _body_length(self, source: SourceFile, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        first = self._first_statement(node)
        span = source.lines[first.lineno - 1 : node.end_lineno]
        return sum(1 for line in span if self._is_code(line))

    def _message(self, node: ast.FunctionDef | ast.AsyncFunctionDef, length: int) -> str:
        return f"'{node.name}' has {length} lines; the limit is {self.MAX_LINES}"

    @staticmethod
    def _first_statement(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.stmt:
        has_docstring = ast.get_docstring(node, clean=False) is not None
        return node.body[1] if has_docstring and len(node.body) > 1 else node.body[0]

    @staticmethod
    def _is_code(line: str) -> bool:
        stripped = line.strip()
        return bool(stripped) and not stripped.startswith("#")
