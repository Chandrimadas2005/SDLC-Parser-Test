from pathlib import Path

from ParserService.Domain.Documents import DocumentStatus
from ParserService.Domain.Jobs import ArtifactPointer, FailureReason, FileName
from ParserService.Infrastructure.Extraction import PdfReader
from ParserService.Infrastructure.Isolation import (
    IsolatedDocumentParser,
    IsolatedParseRunner,
    WorkerFile,
    WorkerLimits,
)
from tests.Samples import SamplePdfs

SECRET = "synthetic-secret"


class TestPasswordUnlock:
    """An encrypted PDF opens with the right password, in the isolated worker too."""

    def test_reader_opens_with_the_right_password_only(self, tmp_path: Path) -> None:
        path = SamplePdfs().encrypted(tmp_path / "locked.pdf")

        opened = PdfReader(password=SECRET).read(path)
        wrong = PdfReader(password="not-it").read(path)

        assert opened.is_ok
        assert wrong.unwrap_err() is FailureReason.PASSWORD_PROTECTED

    def test_worker_uses_the_password_and_then_removes_it(self, tmp_path: Path) -> None:
        folder = tmp_path / "files" / "ab" / "abc"
        folder.mkdir(parents=True)
        SamplePdfs().encrypted(folder / "original.pdf")
        unlock = folder / WorkerFile.UNLOCK
        unlock.write_text(SECRET, encoding="utf-8")
        runner = IsolatedParseRunner(WorkerLimits(timeout_seconds=30, memory_mb=1024))

        outcome = IsolatedDocumentParser(tmp_path, runner).parse(
            ArtifactPointer("files/ab/abc/original.pdf"), FileName("locked.pdf")
        )

        assert outcome.unwrap().status is DocumentStatus.SUCCEEDED
        assert not unlock.exists()
