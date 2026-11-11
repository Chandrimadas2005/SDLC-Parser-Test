from pathlib import Path

from ParserService.Domain.Documents import PropertyName
from ParserService.Infrastructure.Extraction import XlsPropertyReader


class TestXlsPropertyReader:
    """Summary-information properties are read from legacy workbooks; damage adds nothing."""

    ROOT = Path(__file__).parents[2] / "corpus" / "xls"

    def test_reads_author_and_dates_from_the_summary_streams(self) -> None:
        properties = XlsPropertyReader().read(self.ROOT / "normal" / "normal.xls")

        assert properties[PropertyName.CREATOR] == "openpyxl"
        assert properties[PropertyName.CREATED] == "2026-11-11T08:01:09Z"
        assert properties[PropertyName.MODIFIED] == "2026-11-11T08:01:09Z"

    def test_file_that_is_not_a_compound_document_adds_nothing(self) -> None:
        assert XlsPropertyReader().read(self.ROOT / "corrupted" / "corrupted.xls") == {}

    def test_damaged_property_stream_adds_nothing(self) -> None:
        reader = XlsPropertyReader()

        assert reader._safe_parse(b"\x00" * 10, reader.SUMMARY_FIELDS) == {}  # noqa: SLF001
