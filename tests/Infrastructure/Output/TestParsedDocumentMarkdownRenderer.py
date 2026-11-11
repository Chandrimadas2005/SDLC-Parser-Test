from ParserService.Infrastructure.Output.ParsedDocumentMarkdownRenderer import (
    ParsedDocumentMarkdownRenderer,
)


class TestParsedDocumentMarkdownRenderer:
    """Markdown output keeps the result's document identity and structure."""

    def test_renders_metadata_outline_and_table_rows(self) -> None:
        content = (
            b'{"status":"succeeded","document":{"file_name":"sample.csv"},'
            b'"outline":[{"kind":"sheet","name":"Sheet1"}],"warnings":[],'
            b'"elements":[{"kind":"table","rows":[{"row":2,"cells":{"ID":"A1"}}]}]}'
        )
        markdown = ParsedDocumentMarkdownRenderer().render(content)
        assert "**File:** sample.csv" in markdown
        assert "- sheet: Sheet1" in markdown
        assert "**ID:** A1" in markdown
