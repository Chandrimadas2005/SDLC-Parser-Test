from pathlib import Path
from typing import Final

from tests.Samples.OdsPackage import OdsPackage


class OdsCorpusGenerator:
    """Create the synthetic ODS workbooks used by the ODS extractor tests. No real data.

    Run from the repository root with
    ``uv run python -c "from pathlib import Path; from tests.corpus.ods.OdsCorpusGenerator
    import OdsCorpusGenerator; OdsCorpusGenerator().generate(Path('tests/corpus/ods'))"``.
    """

    PACKAGE: Final = OdsPackage()
    HIDDEN_STYLE: Final = "ta-hidden"

    def generate(self, root: Path) -> None:
        """Write normal, hidden, empty, corrupted, partial and wrong-extension fixtures."""
        package = self.PACKAGE
        normal = package.content(self.normal_sheets(), (self.HIDDEN_STYLE,))
        meta = {"dc:title": "Synthetic requirements", "dc:creator": "Synthetic Author"}
        written = package.write(
            root / "normal" / "normal.ods", normal, {"meta.xml": package.meta(meta)}
        )
        self._copy(written.read_bytes(), root / "wrong-extension" / "normal.xlsx")
        hidden = package.sheet("Secret", [package.row([package.text("Only")])], self.HIDDEN_STYLE)
        package.write(
            root / "hidden" / "hidden.ods", package.content([hidden], (self.HIDDEN_STYLE,))
        )
        package.write(root / "empty" / "empty.ods", package.content([package.sheet("Sheet1", [])]))
        self._copy(written.read_bytes()[:400], root / "corrupted" / "truncated.ods")
        broken = normal[: normal.index(b'<table:table table:name="Archive"') + 200]
        package.write(root / "partial-corrupt" / "partial.ods", broken)

    def normal_sheets(self) -> list[str]:
        """Two sheets: requirements with typed values, formulas and merges, and an archive."""
        p = self.PACKAGE
        rows = [p.row(self._header()), *self._requirements(), *self._total()]
        archive = [p.row([p.text("Note")]), p.row([p.text("Archived")])]
        return [p.sheet("Requirements", rows), p.sheet("Archive", archive, self.HIDDEN_STYLE)]

    def _header(self) -> list[str]:
        p = self.PACKAGE
        return [p.text("ID"), p.text("Statement"), p.text("Estimate"), p.text("Due"), p.empty(1020)]

    def _requirements(self) -> list[str]:
        p = self.PACKAGE
        due = p.typed("date", "date-value", "2026-01-31")
        merged = p.text("Shared", 'table:number-rows-spanned="2"')
        flag = p.typed("boolean", "boolean-value", "true")
        return [
            p.row([p.text("REQ-0001"), p.text("Parse HTML"), p.number("3", "of:=1+2"), due]),
            p.row([p.text("REQ-0002"), merged, p.number("5"), flag]),
            p.row([p.text("REQ-0003"), p.covered(), p.number("8")]),
            p.row([p.empty(4)], repeated=2),
        ]

    def _total(self) -> list[str]:
        p = self.PACKAGE
        total = p.text("Total", 'table:number-columns-spanned="2"')
        formula = p.number("16", "of:=SUM([.C2:.C4])")
        return [p.row([total, p.covered(), formula]), p.row([p.empty(1024)], repeated=1_048_000)]

    @staticmethod
    def _copy(content: bytes, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
