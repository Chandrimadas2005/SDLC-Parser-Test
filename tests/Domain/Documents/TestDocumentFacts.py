from ParserService.Domain.Documents import DetectedType, DocumentFacts, PropertyName
from ParserService.Domain.Jobs import FileHash, FileName

FACTS = DocumentFacts(FileName("book.xlsx"), DetectedType.XLSX, 10, FileHash("a" * 64))


class TestDocumentFacts:
    """File properties merge into the facts; empty values never appear."""

    def test_properties_merge_and_later_values_win(self) -> None:
        first = FACTS.with_properties({PropertyName.TITLE: "Old", PropertyName.CREATOR: "A"})

        merged = first.with_properties({PropertyName.TITLE: "New"})

        assert merged.properties == {PropertyName.TITLE: "New", PropertyName.CREATOR: "A"}

    def test_empty_values_are_dropped_but_a_tab_is_kept(self) -> None:
        facts = FACTS.with_properties({PropertyName.TITLE: "", PropertyName.DELIMITER: "\t"})

        assert facts.properties == {PropertyName.DELIMITER: "\t"}

    def test_nothing_to_add_leaves_the_facts_unchanged(self) -> None:
        assert FACTS.with_properties({PropertyName.TITLE: ""}) is FACTS

    def test_declared_language_fills_the_language_fact(self) -> None:
        facts = FACTS.with_properties({PropertyName.LANGUAGE: "en-GB"})

        assert facts.language == "en-GB"
        assert facts.with_properties({PropertyName.LANGUAGE: "fr-FR"}).language == "en-GB"
