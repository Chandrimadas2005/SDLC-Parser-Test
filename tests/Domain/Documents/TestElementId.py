import pytest

from ParserService.Domain.Documents import ElementId


class TestElementId:
    """Element ids are stable, position-based and validated."""

    def test_id_is_built_from_the_position(self) -> None:
        assert str(ElementId.at(1)) == "e-000001"
        assert str(ElementId.at(1_234_567)) == "e-1234567"
        assert ElementId.at(7) == ElementId("e-000007")

    def test_position_starts_at_one(self) -> None:
        with pytest.raises(ValueError, match="starts at 1"):
            ElementId.at(0)

    @pytest.mark.parametrize("value", ["", "e-1", "x-000001", "e-00000a", "e-" + "\u0660" * 6])
    def test_malformed_ids_are_rejected(self, value: str) -> None:
        with pytest.raises(ValueError, match="element id"):
            ElementId(value)
