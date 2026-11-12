import zipfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet


class WorkbookCorpusGenerator:
    """Create synthetic workbooks used by spreadsheet extractor tests."""

    def generate(self, root: Path) -> None:
        """Write normal, hidden, empty, corrupted and wrong-extension fixtures."""
        self._normal(root / "normal" / "normal.xlsx")
        self._hidden(root / "hidden" / "hidden.xlsx")
        self._empty(root / "empty" / "empty.xlsx")
        self._corrupted(root / "corrupted" / "corrupted.xlsx")
        self._partial(root / "partial-corrupt" / "partial.xlsx")
        self._wrong_extension(root / "wrong-extension" / "normal.txt")

    def _normal(self, path: Path) -> None:
        workbook = Workbook()
        sheet = workbook.active
        assert isinstance(sheet, Worksheet)
        sheet.title = "Measurements"
        sheet.append(["Record ID", "Reading", "Total"])
        sheet.append(["REC-001", 4, "=SUM(B2:B2)"])
        sheet.merge_cells("A3:A4")
        sheet["A3"] = "REC-002"
        sheet["B3"] = 6
        sheet["B4"] = 7
        workbook.create_sheet("Archive")
        path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(path)

    def _hidden(self, path: Path) -> None:
        workbook = Workbook()
        sheet = workbook.active
        assert isinstance(sheet, Worksheet)
        sheet.title = "HiddenData"
        sheet.sheet_state = "hidden"
        sheet.append(["Name", "Value"])
        sheet.append(["sample", 1])
        workbook.create_sheet("Visible")
        path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(path)

    def _empty(self, path: Path) -> None:
        workbook = Workbook()
        path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(path)

    def _partial(self, path: Path) -> None:
        self._normal(path)
        temporary = path.with_suffix(".tmp")
        with zipfile.ZipFile(path) as source, zipfile.ZipFile(temporary, "w") as target:
            for item in source.infolist():
                content = (
                    b"<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>"
                    b"<dimension ref='A1:C2'/><sheetData><row r='1'>"
                    b"<c r='A1' s='999999' t='n'><v>1</v></c></row></sheetData>"
                    b"<mergeCells><mergeCell ref='INVALID'/></mergeCells></worksheet>"
                    if item.filename == "xl/worksheets/sheet2.xml"
                    else source.read(item.filename)
                )
                target.writestr(item, content)
        temporary.replace(path)

    def _corrupted(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not a valid xlsx workbook")

    def _wrong_extension(self, path: Path) -> None:
        self._normal(path)


if __name__ == "__main__":
    WorkbookCorpusGenerator().generate(Path(__file__).parent)
