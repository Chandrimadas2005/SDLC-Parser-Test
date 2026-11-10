from pathlib import Path

from tools.CodeRules import RuleName, SourceFile, Violation


class TestViolation:
    """Violations render as clickable ``path:line: CODE message`` lines."""

    def test_render_uses_forward_slashes_and_the_rule_code(self) -> None:
        violation = Violation(
            Path("src") / "Pkg" / "Widget.py", 7, RuleName.METHOD_LENGTH, "too long"
        )

        assert violation.render() == "src/Pkg/Widget.py:7: CR001 too long"

    def test_source_file_keeps_path_tree_and_lines(self) -> None:
        source = SourceFile.parse(Path("Widget.py"), "class Widget:\n    pass\n")

        assert source.path == Path("Widget.py")
        assert source.lines == ("class Widget:", "    pass")
        assert len(source.tree.body) == 1
