import ast
from collections.abc import Iterator
from typing import ClassVar


class FunctionNodes:
    """Finds function definitions and the statements that belong to each one."""

    FUNCTION_TYPES: ClassVar[tuple[type[ast.AST], ...]] = (ast.FunctionDef, ast.AsyncFunctionDef)
    SCOPE_TYPES: ClassVar[tuple[type[ast.AST], ...]] = (*FUNCTION_TYPES, ast.ClassDef, ast.Lambda)

    def functions(self, tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """List every function and method defined anywhere in a tree.

        Args:
            tree: Syntax tree to search.

        Returns:
            The function definitions, outer ones first.
        """
        return [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        ]

    def own_nodes(self, function: ast.AST) -> Iterator[ast.AST]:
        """Yield the nodes of a function, without descending into nested scopes.

        Args:
            function: Function whose own body is walked.

        Yields:
            Every node inside the function that is not inside a nested function or class.
        """
        pending = list(ast.iter_child_nodes(function))
        while pending:
            node = pending.pop()
            yield node
            if not isinstance(node, self.SCOPE_TYPES):
                pending.extend(ast.iter_child_nodes(node))
