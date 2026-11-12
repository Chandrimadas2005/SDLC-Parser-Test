import zipfile
import zlib
from pathlib import Path
from typing import ClassVar

from ParserService.Domain.Documents import DetectedType, DocumentStatus, SourceFile, WarningCode
from ParserService.Domain.Jobs import FailureReason, FileName
from ParserService.Infrastructure.Detection import (
    MagicTypeDetector,
    TextEncodingDetector,
    ZipContentInspector,
)
from ParserService.Infrastructure.Extraction import ExtractorRegistry, ParsePipeline, ZipSalvager
from tests.Samples import SampleDocx, SamplePptx


class _TinySalvager(ZipSalvager):
    MAX_EXPANDED_BYTES: ClassVar[int] = 1_000


class TestRepairingExtractor:
    """Office packages with a damaged table of contents are rebuilt and parsed as partial."""

    PIPELINE = ParsePipeline(
        MagicTypeDetector(TextEncodingDetector(), ZipContentInspector()),
        ExtractorRegistry.default(),
    )

    @staticmethod
    def _damage(path: Path) -> Path:
        data = path.read_bytes()
        path.write_bytes(data[: data.find(b"PK\x01\x02")])
        return path

    def test_damaged_docx_is_repaired_with_all_its_content(self, tmp_path: Path) -> None:
        intact = SampleDocx().normal(tmp_path / "intact.docx")
        damaged = self._damage(SampleDocx().normal(tmp_path / "damaged.docx"))

        good = self.PIPELINE.parse(SourceFile(str(intact), FileName("a.docx"))).unwrap()
        fixed = self.PIPELINE.parse(SourceFile(str(damaged), FileName("a.docx"))).unwrap()

        assert fixed.facts.detected_type is DetectedType.DOCX
        assert fixed.status is DocumentStatus.PARTIAL
        assert [warning.code for warning in fixed.warnings] == [WarningCode.FILE_REPAIRED]
        assert [e.text for e in fixed.elements] == [e.text for e in good.elements]

    def test_damaged_pptx_is_repaired_too(self, tmp_path: Path) -> None:
        damaged = self._damage(SamplePptx().normal(tmp_path / "deck.pptx"))

        document = self.PIPELINE.parse(SourceFile(str(damaged), FileName("deck.pptx"))).unwrap()

        assert WarningCode.FILE_REPAIRED in [warning.code for warning in document.warnings]
        assert document.elements[0].text == "Synthetic deck"

    def test_unrecoverable_package_stays_corrupted(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.docx"
        path.write_bytes(b"PK\x03\x04" + b"\x00" * 26 + b"word/document.xml" + b"\xff" * 40)

        result = self.PIPELINE.parse(SourceFile(str(path), FileName("broken.docx")))

        assert result.unwrap_err() is FailureReason.CORRUPTED_FILE

    def test_salvage_stops_at_the_expansion_cap(self, tmp_path: Path) -> None:
        bomb = tmp_path / "bomb.zip"
        with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("big.txt", b"0" * 50_000)
        self._damage(bomb)

        result = _TinySalvager().salvage(bomb, tmp_path / "out.zip")

        assert result.unwrap_err() is FailureReason.LIMIT_EXCEEDED

    def test_stored_entries_are_recovered_and_unknown_methods_skipped(self, tmp_path: Path) -> None:
        stored = tmp_path / "stored.zip"
        with zipfile.ZipFile(stored, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("note.txt", b"synthetic")
        self._damage(stored)
        odd = tmp_path / "odd.zip"
        odd.write_bytes(
            b"PK\x03\x04" + b"\x00" * 4 + b"\x0c\x00" + b"\x00" * 20 + zlib.compress(b"x")
        )

        rebuilt = tmp_path / "rebuilt.zip"
        assert ZipSalvager().salvage(stored, rebuilt).unwrap() == 1
        assert zipfile.ZipFile(rebuilt).read("note.txt") == b"synthetic"
        assert (
            ZipSalvager().salvage(odd, tmp_path / "x.zip").unwrap_err()
            is FailureReason.CORRUPTED_FILE
        )
