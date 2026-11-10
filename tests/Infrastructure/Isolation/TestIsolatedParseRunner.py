import time
from pathlib import Path
from typing import ClassVar, Final

import pytest

from ParserService.Domain.Documents import DocumentStatus, SourceFile
from ParserService.Domain.Jobs import ArtifactPointer, FailureReason, FileName
from ParserService.Infrastructure.Isolation import (
    IsolatedDocumentParser,
    IsolatedParseRunner,
    ParseWorkerProcess,
    WorkerLimits,
)

CORPUS: Final = Path(__file__).resolve().parents[2] / "corpus"
LIMITS: Final = WorkerLimits(timeout_seconds=30, memory_mb=1024)


class _HangingRunner(IsolatedParseRunner):
    MODULE: ClassVar[str] = "tests.Infrastructure.Isolation.Sleeper"
    GRACE_SECONDS: ClassVar[int] = 0


class _CrashingRunner(IsolatedParseRunner):
    MODULE: ClassVar[str] = "tests.Infrastructure.Isolation.Crasher"


class TestIsolatedParseRunner:
    """Every parse runs in its own process; whatever happens, the caller gets an answer."""

    def test_a_text_file_is_parsed_with_its_cost_measured(self) -> None:
        result = IsolatedParseRunner(LIMITS).run(
            CORPUS / "md/normal/guide.md", FileName("guide.md")
        )

        worker = result.unwrap()
        assert worker.outcome.status is DocumentStatus.SUCCEEDED
        assert b'"detected_type": "md"' in worker.outcome.content
        assert worker.elapsed_ms >= 0
        assert worker.peak_memory_kb > 0

    def test_failure_reported_by_the_worker_is_passed_on(self, tmp_path: Path) -> None:
        path = tmp_path / "blob.bin"
        path.write_bytes(bytes(range(256)) * 4)

        result = IsolatedParseRunner(LIMITS).run(path, FileName("blob.bin"))

        assert result.unwrap_err() is FailureReason.UNSUPPORTED_TYPE

    def test_memory_limit_turns_a_blow_up_into_a_crash(self) -> None:
        tiny = WorkerLimits(timeout_seconds=30, memory_mb=40)

        result = IsolatedParseRunner(tiny).run(CORPUS / "md/normal/guide.md", FileName("guide.md"))

        assert result.unwrap_err() is FailureReason.EXTRACTOR_CRASH

    def test_a_hanging_worker_is_killed_on_timeout(self) -> None:
        started = time.monotonic()

        result = _HangingRunner(WorkerLimits(1, 1024)).run(Path("unused"), FileName("a.txt"))

        assert result.unwrap_err() is FailureReason.TIMEOUT
        assert time.monotonic() - started < 10

    def test_a_crashing_worker_is_reported_as_a_crash(self) -> None:
        result = _CrashingRunner(LIMITS).run(Path("unused"), FileName("a.txt"))

        assert result.unwrap_err() is FailureReason.EXTRACTOR_CRASH

    def test_document_parser_resolves_pointers_inside_the_artifact_root(
        self, tmp_path: Path
    ) -> None:
        stored = tmp_path / "files" / "original.txt"
        stored.parent.mkdir()
        stored.write_text("Stored synthetic text.\n", encoding="utf-8")
        parser = IsolatedDocumentParser(tmp_path, IsolatedParseRunner(LIMITS))

        parsed = parser.parse(ArtifactPointer("files/original.txt"), FileName("notes.txt"))
        missing = parser.parse(ArtifactPointer("files/missing.txt"), FileName("notes.txt"))

        assert parsed.unwrap().status is DocumentStatus.SUCCEEDED
        assert missing.unwrap_err() is FailureReason.EXTRACTOR_CRASH

    def test_worker_rejects_a_wrong_argument_count(self) -> None:
        assert ParseWorkerProcess().run(["only", "two"]) == 2

    def test_worker_writes_a_result_or_a_failure_reason(self, tmp_path: Path) -> None:
        worker = ParseWorkerProcess()
        good, bad = tmp_path / "good", tmp_path / "bad"
        good.mkdir()
        bad.mkdir()
        blob = tmp_path / "blob.bin"
        blob.write_bytes(bytes(range(256)) * 4)

        worker.execute(SourceFile(str(CORPUS / "txt/normal/notes.txt"), FileName("n.txt")), good)
        worker.execute(SourceFile(str(blob), FileName("blob.bin")), bad)

        assert sorted(path.name for path in good.iterdir()) == ["outcome.json", "result.json"]
        assert (bad / "failure.txt").read_text(encoding="utf-8") == "unsupported_type"

    def test_limits_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            WorkerLimits(0, 1024)
