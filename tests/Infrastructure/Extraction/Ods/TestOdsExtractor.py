from pathlib import Path
from typing import Final

from ParserService.Domain.Documents import (
    CellValue,
    ColumnType,
    DocumentStatus,
    Locator,
    MetricName,
    OutlineKind,
    ParseWarning,
    WarningCode,
)
from tests.Infrastructure.Extraction.Ods.OdsHarness import OdsHarness

HARNESS: Final = OdsHarness()
P: Final = OdsHarness.PACKAGE


class TestOdsExtractor:
    """ODS sheets stream into schema 1.1 tables: formulas, merges, hidden flags, profiles."""

    def _normal(self) -> Path:
        return OdsHarness.CORPUS / "normal" / "normal.ods"

    def test_every_sheet_is_outlined_with_its_hidden_flag(self) -> None:
        document = HARNESS.extract(self._normal()).unwrap()

        assert document.status is DocumentStatus.SUCCEEDED
        assert document.facts.sheet_count == 2
        assert [(e.kind, e.name, e.hidden) for e in document.outline] == [
            (OutlineKind.SHEET, "Requirements", False),
            (OutlineKind.SHEET, "Archive", True),
        ]
        assert document.metrics.counts[MetricName.HIDDEN_SHEETS] == 1

    def test_formula_cells_keep_their_formula_and_cached_value(self) -> None:
        document = HARNESS.extract(self._normal()).unwrap()
        table = OdsHarness.table(document)

        assert OdsHarness.cells(table, 2)["Estimate"] == CellValue("3", "of:=1+2", 3)
        total = OdsHarness.cells(table, 7)["Estimate"]
        assert total == CellValue("16", "of:=SUM([.C2:.C4])", 16)
        assert document.metrics.counts[MetricName.FORMULAS] == 2

    def test_merged_cells_are_expanded_and_rows_keep_their_numbers(self) -> None:
        table = OdsHarness.table(HARNESS.extract(self._normal()).unwrap())

        assert OdsHarness.cells(table, 4)["Statement"] == "Shared"
        assert OdsHarness.cells(table, 7)["Statement"] == "Total"
        assert [row.row for row in table.rows] == [2, 3, 4, 5, 6, 7]

    def test_trailing_empty_repeats_do_not_inflate_the_sheet(self) -> None:
        document = HARNESS.extract(self._normal()).unwrap()

        assert document.elements[0].locator == Locator.for_cells("Requirements", "A1:D7")
        assert document.metrics.counts[MetricName.COLUMNS] == 5

    def test_columns_are_profiled_and_values_typed(self) -> None:
        table = OdsHarness.table(HARNESS.extract(self._normal()).unwrap())
        profiles = {profile.name: profile for profile in table.column_profiles}

        assert table.header_row == 1
        assert profiles["ID"].guessed_type is ColumnType.TEXT
        assert profiles["Estimate"].guessed_type is ColumnType.NUMBER
        assert OdsHarness.cells(table, 2)["Due"] == "2026-01-31"

    def test_package_properties_become_file_facts(self) -> None:
        properties = HARNESS.extract(self._normal()).unwrap().facts.properties

        assert properties is not None
        assert properties["title"] == "Synthetic requirements"
        assert properties["creator"] == "Synthetic Author"

    def test_a_broken_stream_keeps_earlier_sheets_and_flags_the_broken_one(self) -> None:
        path = OdsHarness.CORPUS / "partial-corrupt" / "partial.ods"

        document = HARNESS.extract(path).unwrap()

        assert document.status is DocumentStatus.PARTIAL
        assert [entry.name for entry in document.outline] == ["Requirements", "Archive"]
        assert document.warnings == (
            ParseWarning(WarningCode.SHEET_UNREADABLE, Locator.for_cells("Archive", None)),
        )

    def test_cell_text_keeps_spaces_tabs_and_lines_but_not_comments(self, tmp_path: Path) -> None:
        cell = (
            '<table:table-cell office:value-type="string"><text:p>a<text:s text:c="3"/>b'
            "<text:tab/>c</text:p><text:p>second</text:p><office:annotation>"
            "<text:p>reviewer note</text:p></office:annotation></table:table-cell>"
        )
        sheet = P.sheet("Notes", [P.row([cell]), P.row([P.number("1")])])

        table = OdsHarness.table(HARNESS.workbook(tmp_path, [sheet]))

        assert OdsHarness.cells(table, 2)["a   b\tc\nsecond"] == "1"

    def test_booleans_percentages_and_times_are_typed(self, tmp_path: Path) -> None:
        cells = [
            P.typed("boolean", "boolean-value", "false"),
            P.typed("percentage", "value", "0.25"),
            P.typed("time", "time-value", "PT12H30M00S"),
            P.typed("date", "date-value", "2026-01-31T10:00:00"),
        ]
        sheet = P.sheet("Types", [P.row(cells)])

        row = OdsHarness.table(HARNESS.workbook(tmp_path, [sheet])).rows[0]

        assert list(row.cells.values()) == ["False", "0.25", "PT12H30M00S", "2026-01-31T10:00:00"]

    def test_forged_repeat_counts_are_capped(self, tmp_path: Path) -> None:
        wide = P.text("x", 'table:number-columns-repeated="999999999"')
        sheet = P.sheet("Wide", [P.row([wide])])

        document = HARNESS.workbook(tmp_path, [sheet])

        assert document.metrics.counts[MetricName.COLUMNS] == 16_384

    def test_tables_nested_in_cells_and_unnamed_sheets(self, tmp_path: Path) -> None:
        nested = P.sheet("Inner", [P.row([P.text("inner")])])
        cell = (
            '<table:table-cell office:value-type="string">'
            f"<text:p>outer</text:p>{nested}</table:table-cell>"
        )
        sheet = '<table:table table:name="  ">' + P.row([cell]) + "</table:table>"

        document = HARNESS.workbook(tmp_path, [sheet])

        assert [entry.name for entry in document.outline] == ["Sheet1"]
        assert [profile.name for profile in OdsHarness.table(document).column_profiles] == ["outer"]
