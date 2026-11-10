from ParserService.Application.Errors import ApplicationErrorCode
from ParserService.Application.UseCases import GetParseJobStatus
from ParserService.Domain.Jobs import (
    ArtifactPointer,
    Duration,
    FailureReason,
    FileHash,
    FileName,
    Instant,
    Job,
    JobCompletion,
    JobId,
    JobKey,
    JobStatus,
    ParserVersion,
)
from tests.Fakes import InMemoryJobRepository

JOB = Job(
    id=JobId("00000000-0000-4000-8000-000000000002"),
    key=JobKey(FileHash("b" * 64), ParserVersion("0.1.0")),
    file_name=FileName("a.txt"),
    file_pointer=ArtifactPointer("files/bb/original.txt"),
    created_at=Instant(1_000),
)


class TestGetParseJobStatus:
    """Status reflects the job record exactly and unknown jobs are reported as such."""

    def test_unknown_job_is_not_found(self) -> None:
        use_case = GetParseJobStatus(InMemoryJobRepository())

        result = use_case.execute(JobId.new())

        assert result.unwrap_err() is ApplicationErrorCode.JOB_NOT_FOUND

    def test_finished_job_shows_result_and_timings(self) -> None:
        repository = InMemoryJobRepository()
        completion = JobCompletion(JobStatus.SUCCEEDED, ArtifactPointer("results/bb/r.json"), 3)
        repository.add(JOB.start(Instant(2_000)).complete(completion, Instant(2_500)))

        view = GetParseJobStatus(repository).execute(JOB.id).unwrap()

        assert view.status is JobStatus.SUCCEEDED
        assert view.has_result
        assert view.warning_count == 3
        assert view.attempt_count == 1
        assert view.parser_version == ParserVersion("0.1.0")
        assert (view.started_at, view.finished_at) == (Instant(2_000), Instant(2_500))
        assert view.duration == Duration(500)

    def test_failed_job_shows_the_reason_and_no_result(self) -> None:
        repository = InMemoryJobRepository()
        repository.add(JOB.fail(FailureReason.UNSUPPORTED_TYPE, Instant(1_200)))

        view = GetParseJobStatus(repository).execute(JOB.id).unwrap()

        assert view.status is JobStatus.FAILED
        assert view.failure_reason is FailureReason.UNSUPPORTED_TYPE
        assert not view.has_result
        assert view.duration is None
