import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType

import pytest

from ParserService.Domain.Documents import (
    DetectedType,
    Detection,
    DocumentFacts,
    ExtractionRequest,
    ParsedDocument,
    SourceFile,
)
from ParserService.Domain.Jobs import FileHash, FileName
from ParserService.Infrastructure.Extraction.SpreadsheetTableBuilder import SpreadsheetTableBuilder
from ParserService.Infrastructure.Extraction.XlsExtractor import XlsExtractor
from ParserService.Infrastructure.Output.ParsedDocumentJsonEncoder import ParsedDocumentJsonEncoder


@dataclass(frozen=True, slots=True)
class _FakeCell:
    ctype: int
    value: object


@dataclass(frozen=True, slots=True)
class _FakeSheet:
    name: str
    visibility: int
    rows: Sequence[Sequence[_FakeCell]]
    merged_cells: Sequence[tuple[int, int, int, int]] = ()

    def get_rows(self) -> Iterator[Sequence[_FakeCell]]:
        return iter(self.rows)


class _FakeWorkbook:
    def __init__(self, sheets: Sequence[_FakeSheet]) -> None:
        self._sheets = sheets
        self.nsheets = len(sheets)
        self.datemode = 0
        # Same file properties xlrd reports for tests/corpus/xls/normal/normal.xls.
        self.user_name = "Calc"
        self.codepage = 1200
        self.biff_version = 80

    def sheet_by_index(self, index: int) -> _FakeSheet:
        return self._sheets[index]

    def unload_sheet(self, _index: int) -> None:
        return None

    def release_resources(self) -> None:
        return None


class _FakeOpener:
    """Stands in for ``xlrd.open_workbook``; ``None`` simulates a corrupted file."""

    def __init__(self, workbook: _FakeWorkbook | None) -> None:
        self._workbook = workbook

    def __call__(self, filename: str, **options: bool) -> _FakeWorkbook:
        del filename, options
        if self._workbook is None:
            message = "synthetic corrupted workbook"
            raise _FakeXlsError(message)
        return self._workbook


class _FakeXlsError(Exception):
    pass


class TestXlsExtractor:
    """Tests legacy XLS mapping using a synthetic xlrd adapter."""

    ROOT = Path(__file__).parents[2] / "corpus" / "xls"

    def _request(self, path: Path, name: str | None = None) -> ExtractionRequest:
        file_name = FileName(name or path.name)
        facts = DocumentFacts(
            file_name, DetectedType.XLS, path.stat().st_size, FileHash.of(path.read_bytes())
        )
        return ExtractionRequest(
            SourceFile(str(path), file_name), facts, Detection(DetectedType.XLS, None, ())
        )

    def _install_xlrd(
        self, monkeypatch: pytest.MonkeyPatch, workbook: _FakeWorkbook | None
    ) -> None:
        module = ModuleType("xlrd")
        module.__dict__.update(XLRDError=_FakeXlsError, open_workbook=_FakeOpener(workbook))
        monkeypatch.setitem(sys.modules, "xlrd", module)

    def _normal_workbook(self) -> _FakeWorkbook:
        rows = (
            (_FakeCell(1, "Record ID"), _FakeCell(1, "Reading"), _FakeCell(1, "Total")),
            (_FakeCell(1, "REC-001"), _FakeCell(2, 4.0), _FakeCell(2, 4.0)),
            (_FakeCell(1, "REC-002"), _FakeCell(2, 6.0), _FakeCell(0, "")),
            (_FakeCell(0, ""), _FakeCell(2, 7.0), _FakeCell(0, "")),
        )
        return _FakeWorkbook(
            [_FakeSheet("Measurements", 0, rows, ((2, 4, 0, 1),)), _FakeSheet("Archive", 0, ())]
        )

    def test_reads_legacy_table_and_expands_merged_cells(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._install_xlrd(monkeypatch, self._normal_workbook())
        path = self.ROOT / "normal" / "normal.xls"
        document = XlsExtractor(SpreadsheetTableBuilder()).extract(self._request(path)).unwrap()
        table = document.elements[0].table
        assert table is not None
        assert table.header_row == 1
        assert table.rows[0].cells["Total"] == "4.0"
        assert table.rows[2].cells["Record ID"] == "REC-002"
        self._golden(document, "xls_normal.json")

    @pytest.mark.skipif(
        find_spec("xlrd") is None, reason="xlrd runtime dependency is not installed"
    )
    def test_real_xls_file_uses_the_xlrd_adapter(self) -> None:
        path = self.ROOT / "normal" / "normal.xls"
        document = XlsExtractor(SpreadsheetTableBuilder()).extract(self._request(path)).unwrap()
        table = document.elements[0].table
        assert table is not None
        assert table.rows[0].cells["Record ID"] == "REC-001"

    def test_includes_hidden_sheet_outline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        hidden = _FakeSheet("HiddenData", 1, ((_FakeCell(1, "Name"),), (_FakeCell(1, "sample"),)))
        self._install_xlrd(monkeypatch, _FakeWorkbook([hidden]))
        path = self.ROOT / "hidden" / "hidden.xls"
        document = XlsExtractor(SpreadsheetTableBuilder()).extract(self._request(path)).unwrap()
        assert document.outline[0].hidden is True

    def test_corrupted_xls_returns_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._install_xlrd(monkeypatch, None)
        path = self.ROOT / "corrupted" / "corrupted.xls"
        result = XlsExtractor(SpreadsheetTableBuilder()).extract(self._request(path))
        assert result.unwrap_err().value == "corrupted_file"

    def _golden(self, document: ParsedDocument, name: str) -> None:
        path = Path(__file__).parents[2] / "golden" / "extraction" / name
        assert ParsedDocumentJsonEncoder().to_json(document) == path.read_text(encoding="utf-8")
