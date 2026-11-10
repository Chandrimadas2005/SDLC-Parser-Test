from pathlib import Path
from textwrap import dedent

from tools.CodeRules import FunctionNodes, RuleName, SourceFile, TryExceptRule

ONE_TRY = """
def sample() -> None:
    try:
        pass
    except ValueError:
        pass
"""

TWO_TRIES = (
    ONE_TRY
    + """
    try:
        pass
    except KeyError:
        pass
"""
)

NESTED_TRY = (
    ONE_TRY
    + """
    def inner() -> None:
        try:
            pass
        except KeyError:
            pass
"""
)


class TestTryExceptRule:
    """A function may hold at most one try statement; nested scopes count separately."""

    @staticmethod
    def _check(text: str) -> list[tuple[RuleName, int]]:
        source = SourceFile.parse(Path("Sample.py"), dedent(text))
        return [(v.rule, v.line) for v in TryExceptRule(FunctionNodes()).check(source)]

    def test_single_try_passes(self) -> None:
        assert self._check(ONE_TRY) == []

    def test_two_tries_in_one_function_are_reported(self) -> None:
        assert self._check(TWO_TRIES) == [(RuleName.TRY_PER_METHOD, 2)]

    def test_try_in_nested_function_counts_for_that_function_only(self) -> None:
        assert self._check(NESTED_TRY) == []
