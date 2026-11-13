from bs4 import BeautifulSoup
from bs4.element import Tag

from ParserService.Domain.Documents import Confidence, Table, TableRow
from ParserService.Infrastructure.Extraction.Html import HtmlTableReader


class TestHtmlTableReader:
    """HTML tables become data: header names, merged cells expanded, own rows only."""

    READER = HtmlTableReader()

    def _read(self, markup: str) -> Table:
        table = BeautifulSoup(markup, "lxml").find("table")
        assert isinstance(table, Tag)
        return self.READER.read(table)

    def test_a_th_row_names_the_columns(self) -> None:
        table = self._read(
            "<table><thead><tr><th>Name</th><th>Age</th></tr></thead>"
            "<tbody><tr><td>Ada</td><td>37</td></tr></tbody></table>"
        )

        assert table.header_row == 1
        assert table.header_confidence == Confidence(0.95)
        assert table.rows == (TableRow(2, {"Name": "Ada", "Age": "37"}),)

    def test_without_a_header_columns_are_numbered(self) -> None:
        table = self._read("<table><tr><td>a</td><td>b</td></tr><tr><td>c</td></tr></table>")

        assert table.header_row is None
        assert table.rows == (
            TableRow(1, {"column_1": "a", "column_2": "b"}),
            TableRow(2, {"column_1": "c"}),
        )

    def test_merged_cells_are_expanded_across_rows_and_columns(self) -> None:
        table = self._read(
            "<table><tr><th>A</th><th>B</th><th>C</th></tr>"
            "<tr><td rowspan='2'>tall</td><td colspan='2'>wide</td></tr>"
            "<tr><td>x</td><td>y</td></tr></table>"
        )

        assert [dict(row.cells) for row in table.rows] == [
            {"A": "tall", "B": "wide", "C": "wide"},
            {"A": "tall", "B": "x", "C": "y"},
        ]

    def test_a_nested_table_stays_inside_its_cell(self) -> None:
        table = self._read(
            "<table><tr><td>outer<table><tr><td>inner</td></tr></table></td></tr></table>"
        )

        assert table.rows == (TableRow(1, {"column_1": "outer inner"}),)

    def test_blank_or_repeated_header_texts_fall_back_to_numbers(self) -> None:
        table = self._read(
            "<table><tr><th>Key</th><th></th><th>Key</th></tr>"
            "<tr><td>1</td><td>2</td><td>3</td><td>4</td></tr></table>"
        )

        assert table.rows[0].cells == {
            "column_1": "1",
            "column_2": "2",
            "column_3": "3",
            "column_4": "4",
        }

    def test_forged_spans_are_capped_and_invalid_ones_ignored(self) -> None:
        table = self._read(
            "<table><tr><td colspan='999999999'>x</td></tr>"
            "<tr><td rowspan='0'>a</td><td colspan='-3'>b</td></tr></table>"
        )

        assert len(table.rows[0].cells) == HtmlTableReader.MAX_SPAN
        assert table.rows[1].cells == {"column_1": "a", "column_2": "b"}

    def test_an_empty_table_has_no_rows(self) -> None:
        assert self._read("<table></table>") == Table(())
