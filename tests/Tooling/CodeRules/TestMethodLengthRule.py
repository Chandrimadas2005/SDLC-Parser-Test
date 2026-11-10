from pathlib import Path

from tools.CodeRules import FunctionNodes, MethodLengthRule, RuleName, SourceFile


class TestMethodLengthRule:
    """Method bodies longer than 18 code lines are reported; docstrings never count."""

    @staticmethod
    def _source(body_lines: int, preamble: str = "") -> SourceFile:
        body = "".join(f"    x{index} = {index}\n" for index in range(body_lines))
        return SourceFile.parse(Path("Sample.py"), f"def sample() -> None:\n{preamble}{body}")

    def test_body_at_the_limit_passes(self) -> None:
        rule = MethodLengthRule(FunctionNodes())

        assert rule.check(self._source(18)) == []

    def test_body_over_the_limit_is_reported(self) -> None:
        rule = MethodLengthRule(FunctionNodes())

        violations = rule.check(self._source(19))

        assert [(v.rule, v.line) for v in violations] == [(RuleName.METHOD_LENGTH, 1)]
        assert "19 lines" in violations[0].message

    def test_docstring_blank_and_comment_lines_are_not_counted(self) -> None:
        preamble = '    """Docstring.\n\n    Args:\n        none\n    """\n\n    # comment\n\n'
        rule = MethodLengthRule(FunctionNodes())

        assert rule.check(self._source(18, preamble)) == []

    def test_docstring_only_function_passes(self) -> None:
        source = SourceFile.parse(Path("Sample.py"), 'def sample() -> None:\n    """Doc."""\n')

        assert MethodLengthRule(FunctionNodes()).check(source) == []
