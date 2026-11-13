from pathlib import Path
from typing import ClassVar

from ParserService.Domain.Documents import (
    CellValue,
    DetectedType,
    Detection,
    ExtractionRequest,
    ParsedDocument,
    SourceFile,
    Table,
)
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Domain.Ports import Extractor
from ParserService.Infrastructure.Config import Limits
from ParserService.Infrastructure.Extraction import ExtractorRegistry
from tests.Samples import DocumentSamples, OdsPackage


class OdsHarness:
    """Runs the ODS extractor on synthetic packages and reads the results."""

    PACKAGE: ClassVar[OdsPackage] = OdsPackage()
    CORPUS: ClassVar[Path] = Path(__file__).resolve().parents[3] / "corpus" / "ods"

    @staticmethod
    def extractor(limits: Limits | None = None) -> Extractor:
        """The registered ODS extractor."""
        return ExtractorRegistry.default(None, limits).for_type(DetectedType.ODS).unwrap()

    @staticmethod
    def request(path: Path) -> ExtractionRequest:
        """An extraction request for an ODS file."""
        detection = Detection(DetectedType.ODS, None, ())
        facts = DocumentSamples().facts(DetectedType.ODS)
        return ExtractionRequest(SourceFile(str(path), FileName(path.name)), facts, detection)

    def extract(
        self, path: Path, extractor: Extractor | None = None
    ) -> Result[ParsedDocument, FailureReason]:
        """Extract a file with the given or the registered extractor."""
        return (extractor or self.extractor()).extract(self.request(path))

    def workbook(self, tmp_path: Path, sheets: list[str]) -> ParsedDocument:
        """Write a workbook with these sheets and extract it."""
        path = self.PACKAGE.write(tmp_path / "book.ods", self.PACKAGE.content(sheets))
        return self.extract(path).unwrap()

    @staticmethod
    def table(document: ParsedDocument, position: int = 0) -> Table:
        """The table of one element."""
        table = document.elements[position].table
        assert table is not None
        return table

    @staticmethod
    def cells(table: Table, row: int) -> dict[str, str | CellValue]:
        """The cells of the table row with this row number."""
        return dict(next(item for item in table.rows if item.row == row).cells)
