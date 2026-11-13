from pathlib import Path

from bs4 import BeautifulSoup

from ParserService.Domain.Documents import (
    DetectedType,
    Detection,
    DocumentStatus,
    ElementKind,
    ExtractionRequest,
    ImageSource,
    Locator,
    MetricName,
    ParsedDocument,
    SourceFile,
    WarningCode,
)
from ParserService.Domain.Jobs import FileName
from ParserService.Infrastructure.Extraction.Html import (
    HtmlBlockReader,
    HtmlDocumentBuilder,
    HtmlElementPlacer,
    HtmlImageReader,
    HtmlMetadataReader,
    HtmlTableReader,
)
from tests.Samples import DocumentSamples


class TestHtmlDocumentBuilder:
    """HTML becomes elements in reading order, each located in the extracted text."""

    BUILDER = HtmlDocumentBuilder(
        HtmlBlockReader(HtmlTableReader(), HtmlImageReader()),
        HtmlElementPlacer(),
        HtmlMetadataReader(),
    )

    def _parse(self, markup: str) -> ParsedDocument:
        source = SourceFile(str(Path("unused.html")), FileName("unused.html"))
        detection = Detection(DetectedType.HTML, None, ())
        request = ExtractionRequest(source, DocumentSamples().facts(DetectedType.HTML), detection)
        return self.BUILDER.build(request, BeautifulSoup(markup, "lxml"))

    @staticmethod
    def _pairs(document: ParsedDocument) -> list[tuple[ElementKind, str | None]]:
        return [(element.kind, element.text) for element in document.elements]

    def test_headings_paragraphs_nested_lists_and_links_keep_reading_order(self) -> None:
        markup = (
            "<h1>Title</h1><p>Intro</p><ul><li>One<ul><li>Nested</li></ul></li>"
            "<li><p>In a paragraph</p></li></ul><p>See <a href='/x'>Link</a>.</p>"
        )

        document = self._parse(markup)

        assert self._pairs(document) == [
            (ElementKind.HEADING, "Title"),
            (ElementKind.PARAGRAPH, "Intro"),
            (ElementKind.LIST_ITEM, "One"),
            (ElementKind.LIST_ITEM, "Nested"),
            (ElementKind.LIST_ITEM, "In a paragraph"),
            (ElementKind.PARAGRAPH, "See Link."),
            (ElementKind.LINK, "Link"),
        ]
        assert document.elements[0].level == 1
        assert [entry.name for entry in document.outline] == ["Title"]
        assert document.status is DocumentStatus.SUCCEEDED

    def test_text_outside_paragraphs_is_never_lost(self) -> None:
        markup = "<div>Loose <span>text</span> with <b>bo</b>ld</div><section>More</section>tail"

        assert self._pairs(self._parse(markup)) == [
            (ElementKind.PARAGRAPH, "Loose text with bold"),
            (ElementKind.PARAGRAPH, "More"),
            (ElementKind.PARAGRAPH, "tail"),
        ]

    def test_every_locator_points_at_its_text_in_the_extracted_text(self) -> None:
        markup = (
            "<h2>Head</h2><p>Go <a href='/a'>here</a> or <a href='/b'>here</a> now</p>"
            "<table><tr><td>x</td></tr></table><p>Last</p>"
        )
        document = self._parse(markup)
        blocks = [e for e in document.elements if e.kind is not ElementKind.LINK]
        extracted = "\n".join(element.text or "" for element in blocks)

        for element in document.elements:
            start, end = element.locator.char_start, element.locator.char_end
            assert extracted[start:end] == (element.text or "")
        links = [e.locator for e in document.elements if e.kind is ElementKind.LINK]
        assert [link.paragraph for link in links] == [2, 2]
        assert links[0].char_start != links[1].char_start

    def test_scripts_frames_objects_and_unsafe_links_are_skipped_and_reported(self) -> None:
        markup = (
            "<p>Before</p><script>steal()</script><iframe src='x'></iframe>"
            "<object data='x'></object><p>After <a href=' Java\tScript:evil()'>bad</a></p>"
        )

        document = self._parse(markup)

        assert self._pairs(document) == [
            (ElementKind.PARAGRAPH, "Before"),
            (ElementKind.PARAGRAPH, "After bad"),
        ]
        assert [warning.code for warning in document.warnings] == [WarningCode.ELEMENT_SKIPPED] * 4
        assert {warning.locator for warning in document.warnings} == {Locator(paragraph=2)}
        assert document.status is DocumentStatus.SUCCEEDED

    def test_styles_templates_and_comments_are_not_content(self) -> None:
        markup = "<style>p{}</style><p>Kept<!-- hidden --></p><template><p>Inert</p></template>"

        document = self._parse(markup)

        assert self._pairs(document) == [(ElementKind.PARAGRAPH, "Kept")]
        assert document.warnings == ()

    def test_a_skip_before_any_text_points_at_the_first_paragraph(self) -> None:
        document = self._parse(
            "<html><head><script>x()</script></head><body><p>A</p></body></html>"
        )

        assert document.warnings[0].locator == Locator(paragraph=1)

    def test_a_skip_in_a_document_without_text_has_no_locator(self) -> None:
        document = self._parse("<embed src='x'>")

        assert document.elements == ()
        assert document.warnings[0].locator is None

    def test_images_and_links_without_surrounding_text_stand_alone(self) -> None:
        markup = "<div><img src='a.png'></div><p><a href='/x'><img alt=' Logo '></a></p>"

        document = self._parse(markup)

        assert self._pairs(document) == [
            (ElementKind.IMAGE, None),
            (ElementKind.LINK, None),
            (ElementKind.IMAGE, "Logo"),
        ]
        assert [element.locator.paragraph for element in document.elements] == [1, 2, 3]

    def test_links_keep_their_target_and_images_their_source_and_size(self) -> None:
        markup = (
            "<p>See <a href=' /docs/guide '>the guide</a>"
            "<img src='img/chart.png' width='640' height='480px' alt='Chart'>"
            "<img src='data:image/png;base64,AAAA' width='50%' alt='Inline'>"
            "<img alt='No source'></p>"
        )

        elements = self._parse(markup).elements

        assert elements[1].href == "/docs/guide"
        assert elements[2].image == ImageSource("img/chart.png", 640, 480)
        assert elements[3].image is None
        assert elements[4].image is None
        others = [e for e in elements if e.kind is not ElementKind.LINK]
        assert all(element.href is None for element in others)

    def test_anchors_without_href_are_plain_text(self) -> None:
        assert self._pairs(self._parse("<p><a name='top'>Top</a></p>")) == [
            (ElementKind.PARAGRAPH, "Top")
        ]

    def test_line_breaks_and_whitespace_collapse_to_single_spaces(self) -> None:
        document = self._parse("<p>one<br>two\n\n   three&nbsp;four</p>")

        assert self._pairs(document) == [(ElementKind.PARAGRAPH, "one two three four")]

    def test_document_metadata_becomes_file_facts(self) -> None:
        markup = (
            "<html lang='fr'><head><title> Synthetic  title </title>"
            "<meta name='author' content='A. Writer'><meta name='keywords' content='a, b'>"
            "</head><body><p>x</p></body></html>"
        )

        facts = self._parse(markup).facts

        assert facts.language == "fr"
        assert facts.properties == {
            "title": "Synthetic title",
            "author": "A. Writer",
            "keywords": "a, b",
        }

    def test_words_count_text_and_table_cells_but_not_link_text_twice(self) -> None:
        markup = "<p>one <a href='/x'>two three</a></p><table><tr><td>four five</td></tr></table>"

        metrics = self._parse(markup).metrics

        assert metrics.counts[MetricName.WORDS] == 5
        assert metrics.elements_by_kind == {
            ElementKind.PARAGRAPH: 1,
            ElementKind.TABLE: 1,
            ElementKind.LINK: 1,
        }

    def test_empty_and_malformed_markup_still_parse(self) -> None:
        empty = self._parse("")
        malformed = self._parse("<h2>Open<p>text<li>item")

        assert empty.elements == ()
        assert empty.status is DocumentStatus.SUCCEEDED
        assert self._pairs(malformed) == [
            (ElementKind.HEADING, "Open"),
            (ElementKind.PARAGRAPH, "text"),
            (ElementKind.LIST_ITEM, "item"),
        ]

    def test_deeply_nested_markup_does_not_crash(self) -> None:
        depth = 3_000
        document = self._parse("<div>" * depth + "deep" + "</div>" * depth)

        assert document.status is DocumentStatus.SUCCEEDED
        assert all(element.locator.paragraph for element in document.elements)
