import zipfile
from pathlib import Path

from ParserService.Domain.Documents import PropertyName
from ParserService.Infrastructure.Extraction import XlsxPropertyReader

CORE = b"""<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties
  xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/">
  <dc:title>Synthetic budget</dc:title>
  <dc:creator>Sample Author</dc:creator>
  <cp:keywords>synthetic, test</cp:keywords>
  <cp:lastModifiedBy>Sample Editor</cp:lastModifiedBy>
  <dcterms:created>2024-01-02T03:04:05Z</dcterms:created>
  <dc:language>en-GB</dc:language>
  <dc:subject>   </dc:subject>
</cp:coreProperties>"""
APP = b"""<?xml version="1.0" encoding="UTF-8"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Synthetic Office</Application>
  <Company>Example Co</Company>
</Properties>"""


class TestXlsxPropertyReader:
    """Core and extended workbook properties are read; blank or missing parts add nothing."""

    @staticmethod
    def _workbook(tmp_path: Path, parts: dict[str, bytes]) -> Path:
        path = tmp_path / "book.xlsx"
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in parts.items():
                archive.writestr(name, content)
        return path

    def test_reads_core_and_extended_properties(self, tmp_path: Path) -> None:
        path = self._workbook(tmp_path, {"docProps/core.xml": CORE, "docProps/app.xml": APP})

        assert XlsxPropertyReader().read(path) == {
            PropertyName.TITLE: "Synthetic budget",
            PropertyName.CREATOR: "Sample Author",
            PropertyName.KEYWORDS: "synthetic, test",
            PropertyName.LAST_MODIFIED_BY: "Sample Editor",
            PropertyName.CREATED: "2024-01-02T03:04:05Z",
            PropertyName.LANGUAGE: "en-GB",
            PropertyName.APPLICATION: "Synthetic Office",
            PropertyName.COMPANY: "Example Co",
        }

    def test_missing_or_unreadable_parts_add_nothing(self, tmp_path: Path) -> None:
        path = self._workbook(tmp_path, {"docProps/core.xml": b"<not-closed"})

        assert XlsxPropertyReader().read(path) == {}
