import pytest

from ParserService.Domain.Jobs import (
    ArtifactPointer,
    Duration,
    FailureReason,
    FileHash,
    FileName,
    Instant,
    InvalidJobTransitionError,
    Job,
    JobCompletion,
    JobId,
    JobKey,
    JobStatus,
    ParserVersion,
)

QUEUED = Job(
    id=JobId("00000000-0000-4000-8000-000000000001"),
    key=JobKey(FileHash("a" * 64), ParserVersion("0.1.0")),
    file_name=FileName("notes.txt"),
    file_pointer=ArtifactPointer("files/aaaa"),
    created_at=Instant(1_000),
)
COMPLETION = JobCompletion(JobStatus.PARTIAL, ArtifactPointer("results/aaaa.json"), 2)


class TestJob:
    """Job transitions are pure, immutable and refuse impossible moves."""

    def test_new_job_is_queued_with_no_attempts(self) -> None:
        assert QUEUED.status is JobStatus.QUEUED
        assert QUEUED.attempt_count == 0
        assert QUEUED.result_pointer is None

    def test_start_runs_the_job_and_counts_the_attempt(self) -> None:
        running = QUEUED.start(Instant(2_000))

        assert running.status is JobStatus.RUNNING
        assert running.attempt_count == 1
        assert running.started_at == Instant(2_000)
        assert QUEUED.status is JobStatus.QUEUED

    def test_complete_records_result_warnings_and_duration(self) -> None:
        finished = QUEUED.start(Instant(2_000)).complete(COMPLETION, Instant(2_750))

        assert finished.status is JobStatus.PARTIAL
        assert finished.result_pointer == ArtifactPointer("results/aaaa.json")
        assert finished.warning_count == 2
        assert finished.duration == Duration(750)
        assert finished.finished_at == Instant(2_750)

    def test_fail_records_the_reason_from_any_open_state(self) -> None:
        failed_queued = QUEUED.fail(FailureReason.FILE_TOO_LARGE, Instant(1_500))
        failed_running = QUEUED.start(Instant(2_000)).fail(FailureReason.TIMEOUT, Instant(9_000))

        assert failed_queued.failure_reason is FailureReason.FILE_TOO_LARGE
        assert failed_queued.duration is None
        assert failed_running.failure_reason is FailureReason.TIMEOUT
        assert failed_running.duration == Duration(7_000)

    def test_requeue_reopens_a_failed_job_and_keeps_attempts(self) -> None:
        failed = QUEUED.start(Instant(2_000)).fail(FailureReason.EXTRACTOR_CRASH, Instant(3_000))

        requeued = failed.requeue()
        restarted = requeued.start(Instant(4_000))

        assert requeued.status is JobStatus.QUEUED
        assert requeued.failure_reason is None
        assert restarted.attempt_count == 2
        assert restarted.finished_at is None

    def test_start_refuses_a_running_job(self) -> None:
        running = QUEUED.start(Instant(2_000))

        with pytest.raises(InvalidJobTransitionError, match="cannot start a job that is running"):
            running.start(Instant(3_000))

    def test_complete_refuses_a_queued_job(self) -> None:
        with pytest.raises(InvalidJobTransitionError, match="complete"):
            QUEUED.complete(COMPLETION, Instant(3_000))

    def test_fail_refuses_a_finished_job(self) -> None:
        finished = QUEUED.start(Instant(2_000)).complete(COMPLETION, Instant(3_000))

        with pytest.raises(InvalidJobTransitionError) as caught:
            finished.fail(FailureReason.TIMEOUT, Instant(4_000))

        assert caught.value.status is JobStatus.PARTIAL
        assert caught.value.transition == "fail"

    def test_requeue_refuses_a_job_that_did_not_fail(self) -> None:
        with pytest.raises(InvalidJobTransitionError, match="requeue"):
            QUEUED.requeue()
