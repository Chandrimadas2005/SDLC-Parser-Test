import pytest

from ParserService.Domain.Documents import (
    Confidence,
    Element,
    ElementId,
    ElementKind,
    Locator,
    OutlineEntry,
    OutlineKind,
    Table,
    TableRow,
)


class TestElement:
    """Elements, tables and outline entries keep their shape consistent."""

    LOCATOR = Locator.for_page(1)

    def test_heading_needs_a_level_in_range(self) -> None:
        heading = Element(ElementId.at(1), ElementKind.HEADING, self.LOCATOR, "Title", 2)

        assert heading.level == 2
        with pytest.raises(ValueError, match="needs a level"):
            Element(ElementId.at(1), ElementKind.HEADING, self.LOCATOR, "Title")
        with pytest.raises(ValueError, match="1 to 9"):
            Element(ElementId.at(1), ElementKind.HEADING, self.LOCATOR, "Title", 10)

    def test_only_headings_have_a_level(self) -> None:
        with pytest.raises(ValueError, match="only headings"):
            Element(ElementId.at(1), ElementKind.PARAGRAPH, self.LOCATOR, "Text", 1)

    def test_table_data_belongs_to_table_elements_only(self) -> None:
        table = Table(rows=(TableRow(1, {"A": "x"}),))

        assert Element(ElementId.at(1), ElementKind.TABLE, self.LOCATOR, table=table).table
        with pytest.raises(ValueError, match="needs table data"):
            Element(ElementId.at(1), ElementKind.TABLE, self.LOCATOR)
        with pytest.raises(ValueError, match="only tables"):
            Element(ElementId.at(1), ElementKind.PARAGRAPH, self.LOCATOR, table=table)

    def test_header_row_comes_with_its_confidence(self) -> None:
        with pytest.raises(ValueError, match="together"):
            Table(rows=(), header_row=1)
        with pytest.raises(ValueError, match="counted from 1"):
            Table(rows=(), header_row=0, header_confidence=Confidence(0.5))
        with pytest.raises(ValueError, match="counted from 1"):
            TableRow(0, {})

    @pytest.mark.parametrize("value", [-0.1, 1.1, float("nan")])
    def test_confidence_is_between_zero_and_one(self, value: float) -> None:
        with pytest.raises(ValueError, match="between"):
            Confidence(value)

    def test_outline_entries_are_named_and_levelled_like_their_kind(self) -> None:
        sheet = OutlineEntry(OutlineKind.SHEET, "Data", Locator.for_cells("Data", None))

        assert sheet.level is None
        with pytest.raises(ValueError, match="blank"):
            OutlineEntry(OutlineKind.SLIDE, " ", Locator.for_slide(1))
        with pytest.raises(ValueError, match="needs a level"):
            OutlineEntry(OutlineKind.HEADING, "Intro", self.LOCATOR)
