import pytest

from ParserService.Domain.Documents import Locator


class TestLocator:
    """Locators always point somewhere real in the source file."""

    def test_factories_build_each_shape(self) -> None:
        assert Locator.for_page(3).page == 3
        assert Locator.for_cells("Sheet1", "A1:F412").cell_range == "A1:F412"
        assert Locator.for_cells("Archive", None).sheet == "Archive"
        assert Locator.for_slide(2).slide == 2
        assert Locator.for_text(4, 10, 20) == Locator(paragraph=4, char_start=10, char_end=20)

    def test_a_locator_needs_an_anchor(self) -> None:
        with pytest.raises(ValueError, match="needs a page"):
            Locator()

    def test_numbers_are_counted_from_one(self) -> None:
        with pytest.raises(ValueError, match="counted from 1"):
            Locator.for_page(0)
        with pytest.raises(ValueError, match="counted from 1"):
            Locator.for_slide(-1)
        with pytest.raises(ValueError, match="counted from 1"):
            Locator.for_text(0, 0, 0)

    def test_sheet_rules(self) -> None:
        with pytest.raises(ValueError, match="blank"):
            Locator.for_cells("  ", None)
        with pytest.raises(ValueError, match="needs a sheet"):
            Locator(page=1, cell_range="A1")

    def test_offsets_come_in_valid_pairs(self) -> None:
        with pytest.raises(ValueError, match="pair"):
            Locator(paragraph=1, char_start=3)
        with pytest.raises(ValueError, match="start <= end"):
            Locator.for_text(1, 5, 4)
        with pytest.raises(ValueError, match="start <= end"):
            Locator.for_text(1, -1, 4)
