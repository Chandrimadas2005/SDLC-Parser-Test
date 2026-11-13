import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Final

from ParserService.Domain.Documents import DetectedType, ParsedDocument, SourceFile
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Domain.Ports import SummaryGenerator
from ParserService.Infrastructure.Cli import CliDependencies, CliRenderer, ParserCli
from ParserService.Infrastructure.Config import Limits
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import ExtractorRegistry, ParsePipeline
from ParserService.Infrastructure.Output import (
    ParsedDocumentJsonEncoder,
    ParsedDocumentMarkdownRenderer,
)
from ParserService.Infrastructure.Summary import ExtractiveSummaryGenerator
from tests.Fakes import FakeExtractor

CORPUS: Final = Path(__file__).resolve().parents[2] / "corpus"


@dataclass
class CliHarness:
    """A ``ParserCli`` wired to in-memory streams, so tests can read what it printed."""

    pipeline: ParsePipeline | None = None
    generator: SummaryGenerator | None = None
    limits: Limits | None = None
    out: io.StringIO = field(default_factory=io.StringIO)
    errors: io.StringIO = field(default_factory=io.StringIO)

    ARTICLE: ClassVar[Path] = CORPUS / "html" / "normal" / "article.html"
    WORKBOOK: ClassVar[Path] = CORPUS / "ods" / "normal" / "normal.ods"
    TRUNCATED: ClassVar[Path] = CORPUS / "ods" / "corrupted" / "truncated.ods"

    def cli(self) -> ParserCli:
        """The command, wired to this harness's streams."""
        dependencies = CliDependencies(
            pipeline=self.pipeline or ParsePipeline.default(),
            renderer=CliRenderer(ParsedDocumentJsonEncoder(), ParsedDocumentMarkdownRenderer()),
            summary_generator=self.generator or ExtractiveSummaryGenerator(),
            limits=self.limits or Limits(),
            out=self.out,
            errors=self.errors,
        )
        return ParserCli(dependencies)

    def run(self, *arguments: str) -> int:
        """Run ``parser-cli`` with the given arguments."""
        return self.cli().run(list(arguments))

    @staticmethod
    def parsed(path: Path) -> ParsedDocument:
        """What the real pipeline makes of a file."""
        return ParsePipeline.default().parse(SourceFile(str(path), FileName(path.name))).unwrap()

    @staticmethod
    def pipeline_returning(result: Result[ParsedDocument, FailureReason]) -> ParsePipeline:
        """A pipeline whose HTML extractor returns a preset result."""
        detector = MagicTypeDetector(TextEncodingDetector(), ZipContentInspector())
        registry = ExtractorRegistry({DetectedType.HTML: FakeExtractor(result)})
        return ParsePipeline(detector, registry)
