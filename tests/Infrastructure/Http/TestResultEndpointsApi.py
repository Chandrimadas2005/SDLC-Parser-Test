from http import HTTPStatus

from ParserService.Application.UseCases import ArtifactKeys
from ParserService.Domain.Jobs import FailureReason, Instant, JobCompletion, JobId, JobStatus
from tests.Infrastructure.Http.conftest import VERSION, ApiHarness

PATH = "/v1/parse-jobs"


class TestResultEndpointsApi:
    """Result, retry, delete and format endpoints use the shared error envelope."""

    def _completed_job(self, harness: ApiHarness) -> tuple[str, bytes]:
        submitted = harness.client.post(
            PATH, files={"file": ("a.txt", b"source", "text/plain")}
        ).json()
        job = harness.repository.get(JobId(submitted["job_id"]))
        assert job is not None
        pointer = ArtifactKeys().result_json(job.key.file_hash, job.key.parser_version)
        content = (
            b'{"schema_version":"1.2","status":"succeeded",'
            b'"document":{"file_name":"a.txt"},'
            b'"warnings":[],"outline":[],"elements":[],"metrics":{}}'
        )
        harness.store.put(pointer, content)
        running = job.start(Instant(43_000))
        completed = running.complete(
            JobCompletion(JobStatus.SUCCEEDED, pointer, 0), Instant(44_000)
        )
        harness.repository.update(completed)
        return submitted["job_id"], content

    def test_result_json_and_markdown(self, harness: ApiHarness) -> None:
        job_id, content = self._completed_job(harness)
        result = harness.client.get(f"{PATH}/{job_id}/result")
        markdown = harness.client.get(f"{PATH}/{job_id}/result.md")
        assert result.status_code == HTTPStatus.OK
        assert result.content == content
        assert markdown.status_code == HTTPStatus.OK
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert markdown.text.startswith("# Parsed document")

    def test_result_not_ready_uses_error_envelope(self, harness: ApiHarness) -> None:
        job_id = harness.client.post(
            PATH, files={"file": ("a.txt", b"source", "text/plain")}
        ).json()["job_id"]
        response = harness.client.get(f"{PATH}/{job_id}/result")
        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["code"] == "result_not_ready"
        assert response.json()["request_id"]

    def test_retry_failed_job_requeues_it(self, harness: ApiHarness) -> None:
        job_id = harness.client.post(
            PATH, files={"file": ("a.txt", b"source", "text/plain")}
        ).json()["job_id"]
        job = harness.repository.get(JobId(job_id))
        assert job is not None
        failed = job.start(Instant(43_000)).fail(FailureReason.CORRUPTED_FILE, Instant(44_000))
        harness.repository.update(failed)
        harness.queue.items.clear()
        response = harness.client.post(f"{PATH}/{job_id}/retry")
        assert response.status_code == HTTPStatus.ACCEPTED
        assert response.json()["status"] == JobStatus.QUEUED
        assert harness.queue.depth() == 1

    def test_delete_removes_job_and_original_artifact(self, harness: ApiHarness) -> None:
        job_id = harness.client.post(
            PATH, files={"file": ("a.txt", b"source", "text/plain")}
        ).json()["job_id"]
        job = harness.repository.get(JobId(job_id))
        assert job is not None
        assert harness.store.exists(job.file_pointer)
        response = harness.client.delete(f"{PATH}/{job_id}")
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert harness.repository.get(JobId(job_id)) is None
        assert not harness.store.exists(job.file_pointer)

    def test_formats_returns_registered_types_and_parser_version(self, harness: ApiHarness) -> None:
        response = harness.client.get("/v1/formats")
        assert response.status_code == HTTPStatus.OK
        assert response.json()["parser_version"] == VERSION.value
        assert {"xlsx", "xlsm", "xls", "csv", "tsv"}.issubset(response.json()["formats"])
