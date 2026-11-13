from ParserService.Application.Dto import SubmitParseJobCommand
from ParserService.Application.Errors import ApplicationErrorCode
from ParserService.Application.UseCases import (
    ArtifactKeys,
    DeleteParseJob,
    GetParseJobResult,
    JobServices,
    RetryParseJob,
    SubmitParseJob,
    SubmitPolicy,
)
from ParserService.Domain.Jobs import (
    FailureReason,
    FileName,
    Instant,
    JobCompletion,
    JobId,
    JobStatus,
    ParserVersion,
)
from tests.Fakes import FixedClock, InMemoryArtifactStore, InMemoryJobQueue, InMemoryJobRepository


class TestParseJobResultEndpoints:
    """Application behavior behind the result, retry and delete endpoints."""

    def _setup(self) -> tuple[JobServices, ArtifactKeys, JobId]:
        repository, store, queue = (
            InMemoryJobRepository(),
            InMemoryArtifactStore(),
            InMemoryJobQueue(3),
        )
        services = JobServices(repository, store, queue, FixedClock(Instant(10_000)))
        keys = ArtifactKeys()
        submit = SubmitParseJob(services, SubmitPolicy(ParserVersion("1.0"), 1024), keys)
        submitted = submit.execute(
            SubmitParseJobCommand(FileName("sample.txt"), b"synthetic")
        ).unwrap()
        return services, keys, submitted.job_id

    def test_get_result_reports_not_ready_then_reads_artifact(self) -> None:
        services, keys, job_id = self._setup()
        use_case = GetParseJobResult(services.repository, services.store)
        assert use_case.execute(job_id).unwrap_err() is ApplicationErrorCode.RESULT_NOT_READY
        job = services.repository.get(job_id)
        assert job is not None
        pointer = keys.result_json(job.key.file_hash, job.key.parser_version)
        services.store.put(pointer, b'{"status":"succeeded"}')
        completed = job.start(Instant(11_000)).complete(
            JobCompletion(JobStatus.SUCCEEDED, pointer, 0), Instant(12_000)
        )
        services.repository.update(completed)
        assert use_case.execute(job_id).unwrap() == b'{"status":"succeeded"}'

    def test_get_result_of_failed_job_reports_job_failed(self) -> None:
        services, _, job_id = self._setup()
        job = services.repository.get(job_id)
        assert job is not None
        failed = job.start(Instant(11_000)).fail(FailureReason.CORRUPTED_FILE, Instant(12_000))
        services.repository.update(failed)

        result = GetParseJobResult(services.repository, services.store).execute(job_id)

        assert result.unwrap_err() is ApplicationErrorCode.JOB_FAILED

    def test_retry_requeues_only_failed_jobs(self) -> None:
        services, _, job_id = self._setup()
        use_case = RetryParseJob(services)
        assert use_case.execute(job_id).unwrap_err() is ApplicationErrorCode.RETRY_NOT_ALLOWED
        job = services.repository.get(job_id)
        assert job is not None
        failed = job.start(Instant(11_000)).fail(FailureReason.CORRUPTED_FILE, Instant(12_000))
        services.repository.update(failed)
        assert isinstance(services.queue, InMemoryJobQueue)
        services.queue.items.clear()
        result = use_case.execute(job_id).unwrap()
        assert result.status is JobStatus.QUEUED
        assert services.queue.depth() == 1

    def test_delete_removes_job_and_source_artifact(self) -> None:
        services, keys, job_id = self._setup()
        job = services.repository.get(job_id)
        assert job is not None
        assert services.store.exists(job.file_pointer)
        assert DeleteParseJob(services, keys).execute(job_id).unwrap() == job_id
        assert services.repository.get(job_id) is None
        assert not services.store.exists(job.file_pointer)
