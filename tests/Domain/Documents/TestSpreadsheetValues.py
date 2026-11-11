import pytest

from ParserService.Domain.Documents import ColumnProfile, ColumnType, OutlineEntry, OutlineKind
from ParserService.Domain.Documents.Locator import Locator


class TestSpreadsheetValues:
    """Spreadsheet value objects reject invalid profile and outline data."""

    def test_column_profile_checks_fill_rate_and_unique_count(self) -> None:
        with pytest.raises(ValueError, match="fill rate"):
            ColumnProfile("Amount", ColumnType.NUMBER, 1.1, 2, False)
        with pytest.raises(ValueError, match="unique value"):
            ColumnProfile("Amount", ColumnType.NUMBER, 1.0, -1, False)

    def test_hidden_flag_is_restricted_to_sheet_outline_entries(self) -> None:
        with pytest.raises(ValueError, match="only sheet"):
            OutlineEntry(OutlineKind.HEADING, "Title", Locator.for_text(1, 0, 5), hidden=True)
