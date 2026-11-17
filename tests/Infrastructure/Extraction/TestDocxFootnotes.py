from pathlib import Path

from ParserService.Domain.Documents import ElementKind, SourceFile
from ParserService.Domain.Jobs import FileName
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import ExtractorRegistry, ParsePipeline
from tests.Samples import SampleDocx


class TestDocxFootnotes:
    """A footnote reference becomes its own element, anchored to its paragraph."""

    PIPELINE = ParsePipeline(
        MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
        ExtractorRegistry.default(),
    )

    def test_footnote_text_appears_as_its_own_element(self, tmp_path: Path) -> None:
        path = SampleDocx().footnote(tmp_path / "notes.docx")

        document = self.PIPELINE.parse(SourceFile(str(path), FileName(path.name))).unwrap()

        kinds = [(element.kind, element.text) for element in document.elements]
        assert kinds == [
            (ElementKind.HEADING, "Synthetic report"),
            (ElementKind.PARAGRAPH, "See the note."),
            (ElementKind.FOOTNOTE, "Synthetic footnote text"),
        ]
