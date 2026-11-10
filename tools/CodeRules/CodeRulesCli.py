import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Self, TextIO

from tools.CodeRules.CodeRulesChecker import CodeRulesChecker
from tools.CodeRules.FunctionNodes import FunctionNodes
from tools.CodeRules.MethodLengthRule import MethodLengthRule
from tools.CodeRules.ModuleLayoutRule import ModuleLayoutRule
from tools.CodeRules.PackageInitRule import PackageInitRule
from tools.CodeRules.TryExceptRule import TryExceptRule


class CodeRulesCli:
    """Command line entry point: ``python -m tools.CodeRules <directory> [...]``."""

    EXIT_CLEAN: Final = 0
    EXIT_VIOLATIONS: Final = 1

    def __init__(self, checker: CodeRulesChecker, output: TextIO) -> None:
        self._checker = checker
        self._output = output

    @classmethod
    def default(cls, output: TextIO | None = None) -> Self:
        """Build the command with every repository rule.

        Args:
            output: Where violations are written; standard output when omitted.

        Returns:
            A ready-to-run command.
        """
        function_nodes = FunctionNodes()
        file_rules = (
            MethodLengthRule(function_nodes),
            TryExceptRule(function_nodes),
            ModuleLayoutRule(),
        )
        checker = CodeRulesChecker(file_rules, (PackageInitRule(),))
        return cls(checker, output or sys.stdout)

    def run(self, arguments: Sequence[str]) -> int:
        """Check the given directories and report every violation.

        Args:
            arguments: Directories to check.

        Returns:
            ``EXIT_CLEAN`` when nothing was found, otherwise ``EXIT_VIOLATIONS``.
        """
        violations = self._checker.check([Path(argument) for argument in arguments])
        self._output.writelines(f"{violation.render()}\n" for violation in violations)
        return self.EXIT_VIOLATIONS if violations else self.EXIT_CLEAN
